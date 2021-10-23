"""Configuraitons for laminar data sources."""

import dataclasses
import hashlib
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator, Iterable, List, Sequence

import cloudpickle
from dacite.core import from_dict

from laminar.utils import fs

if TYPE_CHECKING:
    from laminar.components import Layer
else:
    Layer = "Layer"


@dataclasses.dataclass(frozen=True)
class Artifact:
    """Handler for artifacts in the laminar datastore.

    Notes:
        Artifacts are gziped, pickled layer instance attributes.
    """

    hexdigest: str

    @staticmethod
    def root(root: str) -> str:
        return os.path.join(root, "artifacts")

    def uri(self, root: str) -> str:
        return os.path.join(Artifact.root(root), f"{self.hexdigest}.gz")

    def read(self, root: str) -> Any:
        with fs.open(self.uri(root), "rb") as file:
            return cloudpickle.load(file)

    def write(self, root: str, content: bytes) -> None:
        with fs.open(self.uri(root), "wb") as file:
            file.write(content)


@dataclasses.dataclass(frozen=True)
class Archive:
    """Handler for archives in the laminar datastore.

    Notes:
        Archives are metadata for artifacts.r
    """

    artifacts: List[Artifact]

    @staticmethod
    def uri(root: str, layer: Layer, name: str) -> str:
        return os.path.join(root, layer.flow.name, layer.flow.execution, layer.name, f"{name}.json")

    @staticmethod
    def read(root: str, layer: Layer, name: str) -> "Archive":
        with fs.open(Archive.uri(root, layer, name), "r") as file:
            return from_dict(Archive, json.load(file))

    def write(self, root: str, layer: Layer, name: str) -> None:
        with fs.open(Archive.uri(root, layer, name), "w") as file:
            json.dump(dataclasses.asdict(self), file)


@dataclasses.dataclass(frozen=True)
class Accessor:
    """Artifact handler for forked artifacts."""

    archive: Archive
    layer: "Layer"

    def __getitem__(self, key: int) -> Any:
        with fs.open(self.archive.artifacts[key].uri(self.layer.flow.datastore.root), "rb") as file:
            return cloudpickle.load(file)

    def __iter__(self) -> Generator[Any, None, None]:
        for artifact in self.archive.artifacts:
            with fs.open(artifact.uri(self.layer.flow.datastore.root), "rb") as file:
                yield cloudpickle.load(file)

    def __len__(self) -> int:
        return len(self.archive.artifacts)


@dataclasses.dataclass(frozen=True)
class DataStore:
    root: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.rstrip("/"))

    def _read(self, layer: Layer, name: str) -> Any:
        archive = Archive.read(self.root, layer, name)

        # Read the artifact value
        if len(archive.artifacts) == 1:
            return archive.artifacts[0].read(self.root)

        # Create an accessor for the artifacts
        else:
            return Accessor(archive=archive, layer=layer)

    def read(self, layer: Layer, name: str) -> Any:
        """Read an artifact from the laminar datastore.

        Args:
            layer: Layer being read from.
            name: Name of the artifact being read.

        Returns:
            Any: Value of the artifact.
        """

        return self._read(layer, name)

    def _write(self, layer: Layer, name: str, values: Iterable[Any]) -> None:
        contents = [cloudpickle.dumps(value) for value in values]
        archive = Archive(artifacts=[Artifact(hexdigest=hashlib.sha256(content).hexdigest()) for content in contents])

        archive.write(self.root, layer, name)

        # Write the artifact(s) value
        for artifact, content in zip(archive.artifacts, contents):
            artifact.write(self.root, content)

    def write(self, layer: Layer, name: str, values: Iterable[Any]) -> None:
        """Write an artifact to the laminar datastore.

        Args:
            layer: Layer being written to.
            name: Name of the artifact being written.
            values : Artifact values to store.
        """

        self._write(layer, name, values)


@dataclasses.dataclass(frozen=True)
class Local(DataStore):
    """Store the laminar workspace on the local filesystem."""

    root: str = str(Path.cwd() / ".laminar")

    def write(self, layer: Layer, name: str, values: Sequence[Any]) -> None:
        Path(Archive.uri(self.root, layer, name)).parent.mkdir(parents=True, exist_ok=True)
        Path(Artifact.root(self.root)).mkdir(parents=True, exist_ok=True)

        self._write(layer, name, values)


@dataclasses.dataclass(frozen=True)
class S3(DataStore):
    """Store the laminar workspace in AWS S3."""
