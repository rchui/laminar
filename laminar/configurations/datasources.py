"""Configuraitons for laminar data sources."""

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, List, Sequence

import cloudpickle
from pydantic import BaseModel

from laminar.utils import fs


class Artifact(BaseModel):
    """Metadata for laminar artifacts."""

    hexdigest: str

    @staticmethod
    def root(root: str) -> str:
        return os.path.join(root, "artifacts")

    def uri(self, root: str) -> str:
        return os.path.join(self.root(root), f"{self.hexdigest}.gz")


class Archive(BaseModel):
    """Metadata for laminar archives."""

    artifacts: List[Artifact]

    @staticmethod
    def uri(*, root: str, flow: str, execution: str, layer: str, artifact: str) -> str:
        return os.path.join(root, flow, execution, layer, f"{artifact}.json")


class Accessor(BaseModel):
    """Artifact handler for forked artifacts."""

    archive: Archive
    datasource: "DataSource"

    def __getitem__(self, key: int) -> Any:
        with fs.open(self.archive.artifacts[key].uri(self.datasource.root), "rb") as file:
            return cloudpickle.load(file)

    def __iter__(self) -> Iterator[Any]:  # type: ignore
        for artifact in self.archive.artifacts:
            with fs.open(artifact.uri(self.datasource.root), "rb") as file:
                yield cloudpickle.load(file)

    def __len__(self) -> int:
        return len(self.archive.artifacts)


@dataclass(frozen=True)
class DataSource:
    root: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.rstrip("/"))

    def _read(self, uri: str) -> Any:
        # Read the archive
        with fs.open(uri, "r") as file:
            archive = Archive.parse_raw(file.read())

        # Read the artifact value
        if len(archive.artifacts) == 1:
            with fs.open(archive.artifacts[0].uri(self.root), "rb") as file:
                return cloudpickle.load(file)

        # Create an accessor for the artifacts
        else:
            return Accessor(archive=archive, datasource=self)

    def read(self, *, flow: str, execution: str, layer: str, artifact: str) -> Any:
        """Read an artifact from the laminar datasource.

        Args:
            flow: Name of the flow
            execution: Flow execution ID
            layer: Name of the layer
            artifact: Name of the artifact

        Returns:
            Any: Value of the artifact.
        """

        return self._read(Archive.uri(root=self.root, flow=flow, execution=execution, layer=layer, artifact=artifact))

    def _write(self, uri: str, values: Sequence[Any]) -> None:
        contents = [cloudpickle.dumps(value) for value in values]
        archive = Archive(artifacts=[Artifact(hexdigest=hashlib.sha256(content).hexdigest()) for content in contents])

        # Write the archive
        with fs.open(uri, "w") as file:
            file.write(archive.json())

        # Write the artifact(s) value
        for artifact, content in zip(archive.artifacts, contents):
            with fs.open(artifact.uri(self.root), "wb") as file:
                file.write(content)

    def write(self, *, flow: str, execution: str, layer: str, artifact: str, values: Sequence[Any]) -> None:
        """Write an artifact to the laminar datasource.

        Args:
            flow: Name of the flow
            execution: Flow execution ID
            layer: Name of the layer
            artifact: Name of the artifact
            values : Artifact values to store
        """

        self._write(Archive.uri(root=self.root, flow=flow, execution=execution, layer=layer, artifact=artifact), values)


@dataclass(frozen=True)
class Local(DataSource):
    """Store the laminar workspace on the local filesystem."""

    root: str = str(Path.cwd() / ".laminar")

    def write(self, *, flow: str, execution: str, layer: str, artifact: str, values: Sequence[Any]) -> None:
        uri = Archive.uri(root=self.root, flow=flow, execution=execution, layer=layer, artifact=artifact)

        Path(uri).parent.mkdir(parents=True, exist_ok=True)
        Path(Artifact.root(self.root)).mkdir(parents=True, exist_ok=True)

        self._write(uri, values)


@dataclass(frozen=True)
class S3(DataSource):
    """Store the laminar workspace in AWS S3."""
