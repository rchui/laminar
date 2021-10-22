"""Configuraitons for laminar data sources."""

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Generator, List, Sequence

import cloudpickle
from dacite import from_dict

from laminar.utils import fs


@dataclass(frozen=True)
class Artifact:
    """Metadata for laminar artifacts."""

    hexdigest: str

    @staticmethod
    def root(root: str) -> str:
        return os.path.join(root, "artifacts")

    def uri(self, root: str) -> str:
        return os.path.join(self.root(root), f"{self.hexdigest}.gz")


@dataclass(frozen=True)
class Archive:
    """Metadata for laminar archives."""

    artifacts: List[Artifact]

    @staticmethod
    def uri(*, root: str, flow: str, execution: str, layer: str, artifact: str) -> str:
        return os.path.join(root, flow, execution, layer, f"{artifact}.json")


@dataclass(frozen=True)
class Accessor:
    """Artifact handler for forked artifacts."""

    archive: Archive
    datastore: "DataStore"

    def __getitem__(self, key: int) -> Any:
        with fs.open(self.archive.artifacts[key].uri(self.datastore.root), "rb") as file:
            return cloudpickle.load(file)

    def __iter__(self) -> Generator[Any, None, None]:
        for artifact in self.archive.artifacts:
            with fs.open(artifact.uri(self.datastore.root), "rb") as file:
                yield cloudpickle.load(file)

    def __len__(self) -> int:
        return len(self.archive.artifacts)


@dataclass(frozen=True)
class DataStore:
    root: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.rstrip("/"))

    def _read(self, uri: str) -> Any:
        # Read the archive
        with fs.open(uri, "r") as file:
            archive = from_dict(Archive, json.load(file))

        # Read the artifact value
        if len(archive.artifacts) == 1:
            with fs.open(archive.artifacts[0].uri(self.root), "rb") as file:
                return cloudpickle.load(file)

        # Create an accessor for the artifacts
        else:
            return Accessor(archive=archive, datastore=asdict(self))

    def read(self, *, flow: str, execution: str, layer: str, artifact: str) -> Any:
        """Read an artifact from the laminar datastore.

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
            json.dump(asdict(archive), file)

        # Write the artifact(s) value
        for artifact, content in zip(archive.artifacts, contents):
            with fs.open(artifact.uri(self.root), "wb") as file:
                file.write(content)

    def write(self, *, flow: str, execution: str, layer: str, artifact: str, values: Sequence[Any]) -> None:
        """Write an artifact to the laminar datastore.

        Args:
            flow: Name of the flow
            execution: Flow execution ID
            layer: Name of the layer
            artifact: Name of the artifact
            values : Artifact values to store
        """

        self._write(Archive.uri(root=self.root, flow=flow, execution=execution, layer=layer, artifact=artifact), values)


@dataclass(frozen=True)
class Local(DataStore):
    """Store the laminar workspace on the local filesystem."""

    root: str = str(Path.cwd() / ".laminar")

    def write(self, *, flow: str, execution: str, layer: str, artifact: str, values: Sequence[Any]) -> None:
        uri = Archive.uri(root=self.root, flow=flow, execution=execution, layer=layer, artifact=artifact)

        Path(uri).parent.mkdir(parents=True, exist_ok=True)
        Path(Artifact.root(self.root)).mkdir(parents=True, exist_ok=True)

        self._write(uri, values)


@dataclass(frozen=True)
class S3(DataStore):
    """Store the laminar workspace in AWS S3."""