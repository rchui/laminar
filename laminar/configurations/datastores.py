"""Configuraitons for laminar data sources."""

import dataclasses
import hashlib
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Sequence, Union, overload

import cloudpickle
import yaml
from dacite.core import from_dict

from laminar.utils import fs

if TYPE_CHECKING:
    from laminar import Layer
else:
    Layer = "Layer"


@dataclasses.dataclass(frozen=True)
class Artifact:
    """Handler for artifacts in the laminar datastore.

    Notes:
        Artifacts are gziped, pickled layer instance attributes.
    """

    hexdigest: str

    def path(self, *, layer: Layer) -> str:
        return os.path.join(layer.flow.name, "artifacts", f"{self.hexdigest}.gz")

    def dict(self) -> Dict[str, str]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class Archive:
    """Handler for archives in the laminar datastore.

    Notes:
        Archives are metadata for artifacts.
    """

    artifacts: List[Artifact]

    def __len__(self) -> int:
        return len(self.artifacts)

    @staticmethod
    def path(*, layer: Layer, index: int, name: str) -> str:
        assert layer.flow.execution is not None
        return os.path.join(layer.flow.name, "archives", layer.flow.execution, layer.name, str(index), f"{name}.yaml")

    def dict(self) -> Dict[str, List[Dict[str, str]]]:
        return dataclasses.asdict(self)

    @staticmethod
    def parse(source: Dict[str, List[Dict[str, str]]]) -> "Archive":
        return from_dict(Archive, source)


@dataclasses.dataclass(frozen=True)
class Accessor:
    """Artifact handler for sharded artifacts."""

    archive: Archive
    layer: "Layer"

    @overload
    def __getitem__(self, key: int) -> Any:
        ...

    @overload
    def __getitem__(self, key: slice) -> List[Any]:
        ...

    def __getitem__(self, key: Union[int, slice]) -> Any:
        # Directly access an index
        if isinstance(key, int):
            if key >= len(self.archive):
                raise IndexError

            return self.layer.flow.configuration.datastore._read_artifact(
                path=self.archive.artifacts[key].path(layer=self.layer)
            )

        # Slicing for multiple splits
        elif isinstance(key, slice):
            values: List[Any] = []
            for artifact in self.archive.artifacts[key]:
                values.append(
                    self.layer.flow.configuration.datastore._read_artifact(path=artifact.path(layer=self.layer))
                )
            return values

        else:
            raise TypeError(f"{type(key)} is not a valid key type for Accessor.__getitem__")

    def __iter__(self) -> Generator[Any, None, None]:
        for artifact in self.archive.artifacts:
            yield self.layer.flow.configuration.datastore._read_artifact(path=artifact.path(layer=self.layer))

    def __len__(self) -> int:
        return len(self.archive)


@dataclasses.dataclass(frozen=True)
class DataStore:
    root: str

    def __post_init__(self) -> None:
        if not self.root.endswith(("://", ":///")):
            object.__setattr__(self, "root", self.root.rstrip("/"))

    def uri(self, *, path: str) -> str:
        return os.path.join(self.root, path)

    def exists(self, *, uri: str) -> bool:
        return fs.exists(uri=uri)

    def _read_archive(self, *, path: str) -> Archive:
        with fs.open(self.uri(path=path), "r") as file:
            return Archive.parse(yaml.safe_load(file))

    def read_archive(self, *, layer: Layer, index: int, name: str) -> Archive:
        """Read an archive from the laminar datastore.

        Args:
            layer: Layer being read from.
            index: Layer index being read from.
            name: Name of the artifact the archive is for.

        Returns:
            Archive: Archive of the requested artifact.
        """

        return self._read_archive(path=Archive.path(layer=layer, index=index, name=name))

    def _read_artifact(self, *, path: str) -> Any:
        with fs.open(self.uri(path=path), "rb") as file:
            return cloudpickle.load(file)

    def read_artifact(self, *, layer: Layer, archive: Archive) -> Any:
        """REad an artifact form the laminar datastore.

        Args:
            layer (Layer): Layer being read from.
            archive (Archive): Archive to reference the artifact from.

        Returns:
            Any: Artifact value.
        """

        # Read the artifact value
        if len(archive) == 1:
            return self._read_artifact(path=archive.artifacts[0].path(layer=layer))

        # Create an accessor for the artifacts
        else:
            return Accessor(archive=archive, layer=layer)

    def read(self, *, layer: Layer, index: int, name: str) -> Any:
        """Read an artifact from the laminar datastore.

        Args:
            layer: Layer being read from.
            index: Layer index being read from.
            name: Name of the artifact being read.

        Returns:
            Any: Value of the artifact.
        """

        return self.read_artifact(layer=layer, archive=self.read_archive(layer=layer, index=index, name=name))

    def _write_archive(self, *, path: str, archive: Archive) -> None:
        with fs.open(self.uri(path=path), "w") as file:
            yaml.safe_dump(archive.dict(), file)

    def _write_artifact(self, *, path: str, content: bytes) -> None:
        with fs.open(self.uri(path=path), "wb") as file:
            file.write(content)

    def write(self, *, layer: Layer, name: str, values: Sequence[Any]) -> None:
        """Write an artifact to the laminar datastore.

        Args:
            layer: Layer being written to.
            name: Name of the artifact being written.
            values : Artifact values to store.
        """

        artifacts = {
            Artifact(hexdigest=hashlib.sha256(content).hexdigest()): content
            for content in (cloudpickle.dumps(value) for value in values)
        }
        archive = Archive(artifacts=list(artifacts.keys()))

        assert layer.index is not None
        self._write_archive(path=Archive.path(layer=layer, index=layer.index, name=name), archive=archive)

        # Write the artifact(s) value
        for artifact, content in artifacts.items():
            self._write_artifact(path=artifact.path(layer=layer), content=content)


@dataclasses.dataclass(frozen=True)
class Local(DataStore):
    """Store the laminar workspace on the local filesystem."""

    root: str = str(Path.cwd() / ".laminar")


@dataclasses.dataclass(frozen=True)
class S3(DataStore):
    """Store the laminar workspace in AWS S3."""


@dataclasses.dataclass(frozen=True)
class Memory(DataStore):
    """Store the laminar workspace in memory."""

    root: str = "memory:///"
    workspace: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def exists(self, *, uri: str) -> bool:
        return uri in self.workspace

    def _read_archive(self, *, path: str) -> Archive:
        return self.workspace[self.uri(path=path)]

    def _write_archive(self, *, path: str, archive: Archive) -> None:
        self.workspace[self.uri(path=path)] = archive

    def _read_artifact(self, *, path: str) -> Any:
        return self.workspace[self.uri(path=path)]

    def _write_artifact(self, *, path: str, content: bytes) -> None:
        self.workspace[self.uri(path=path)] = cloudpickle.loads(content)
