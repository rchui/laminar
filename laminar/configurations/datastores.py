"""Configuraitons for laminar data sources."""

import dataclasses
import hashlib
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator, List, Sequence, Union, overload

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
    def root(*, root: str) -> str:
        return os.path.join(root, "artifacts")

    def uri(self, *, root: str) -> str:
        return os.path.join(Artifact.root(root=root), f"{self.hexdigest}.gz")

    def read(self, *, root: str) -> Any:
        with fs.open(self.uri(root=root), "rb") as file:
            return cloudpickle.load(file)

    def write(self, *, root: str, content: bytes) -> None:
        with fs.open(self.uri(root=root), "wb") as file:
            file.write(content)


@dataclasses.dataclass(frozen=True)
class Archive:
    """Handler for archives in the laminar datastore.

    Notes:
        Archives are metadata for artifacts.r
    """

    artifacts: List[Artifact]

    @overload
    def __getitem__(self, key: int) -> Artifact:
        ...

    @overload
    def __getitem__(self, key: slice) -> List[Artifact]:
        ...

    def __getitem__(self, key: Union[int, slice]) -> Union[Artifact, List[Artifact]]:
        if isinstance(key, int):
            if key >= len(self):
                raise IndexError

            return self.artifacts[key]

        elif isinstance(key, slice):
            return self.artifacts[key]

        else:
            raise TypeError(f"{type(key)} is not a valid key for Archive.__getitem__")

    def __iter__(self) -> Generator[Artifact, None, None]:
        for artifact in self.artifacts:
            yield artifact

    def __len__(self) -> int:
        return len(self.artifacts)

    @staticmethod
    def uri(*, root: str, layer: Layer, index: int, name: str) -> str:
        assert layer.flow.execution is not None
        return os.path.join(root, layer.flow.name, layer.flow.execution, layer.name, str(index), f"{name}.json")

    @staticmethod
    def read(*, root: str, layer: Layer, index: int, name: str) -> "Archive":
        with fs.open(Archive.uri(root=root, layer=layer, index=index, name=name), "r") as file:
            return from_dict(Archive, json.load(file))

    def write(self, *, root: str, layer: Layer, name: str) -> None:
        assert layer.index is not None

        with fs.open(Archive.uri(root=root, layer=layer, index=layer.index, name=name), "w") as file:
            json.dump(dataclasses.asdict(self), file)


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

            with fs.open(self.archive[key].uri(root=self.layer.flow.configuration.datastore.root), "rb") as file:
                return cloudpickle.load(file)

        # Slicing for multiple indexes
        elif isinstance(key, slice):
            values: List[Any] = []
            for artifact in self.archive[key]:
                with fs.open(artifact.uri(root=self.layer.flow.configuration.datastore.root), "rb") as file:
                    values.append(cloudpickle.load(file))
            return values

        else:
            raise TypeError(f"{type(key)} is not a valid key for Accessor.__getitem__")

    def __iter__(self) -> Generator[Any, None, None]:
        for artifact in self.archive:
            with fs.open(artifact.uri(root=self.layer.flow.configuration.datastore.root), "rb") as file:
                yield cloudpickle.load(file)

    def __len__(self) -> int:
        return len(self.archive)


@dataclasses.dataclass(frozen=True)
class DataStore:
    root: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.rstrip("/"))

    def read_archive(self, *, layer: Layer, index: int, name: str) -> Archive:
        """Read an archive from the laminar datastore.

        Args:
            layer (Layer): Layer being read from.
            index (int): Layer index being read from.
            name (str): Name of the artifact the archive is for.

        Returns:
            Archive: Archive of the requested artifact.
        """

        return Archive.read(root=self.root, layer=layer, index=index, name=name)

    def _read_artifact(self, *, layer: Layer, archive: Archive) -> Any:
        # Read the artifact value
        if len(archive) == 1:
            return archive[0].read(root=self.root)

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

        return self._read_artifact(layer=layer, archive=self.read_archive(layer=layer, index=index, name=name))

    def _write(self, *, layer: Layer, name: str, values: Sequence[Any]) -> None:
        contents = [cloudpickle.dumps(value) for value in values]
        archive = Archive(artifacts=[Artifact(hexdigest=hashlib.sha256(content).hexdigest()) for content in contents])

        archive.write(root=self.root, layer=layer, name=name)

        # Write the artifact(s) value
        for artifact, content in zip(archive, contents):
            artifact.write(root=self.root, content=content)

    def write(self, *, layer: Layer, name: str, values: Sequence[Any]) -> None:
        """Write an artifact to the laminar datastore.

        Args:
            layer: Layer being written to.
            name: Name of the artifact being written.
            values : Artifact values to store.
        """

        self._write(layer=layer, name=name, values=values)


@dataclasses.dataclass(frozen=True)
class Local(DataStore):
    """Store the laminar workspace on the local filesystem."""

    root: str = str(Path.cwd() / ".laminar")

    def write(self, *, layer: Layer, name: str, values: Sequence[Any]) -> None:
        assert layer.index is not None

        Path(Archive.uri(root=self.root, layer=layer, index=layer.index, name=name)).parent.mkdir(
            parents=True, exist_ok=True
        )
        Path(Artifact.root(root=self.root)).mkdir(parents=True, exist_ok=True)

        self._write(layer=layer, name=name, values=values)


@dataclasses.dataclass(frozen=True)
class S3(DataStore):
    """Store the laminar workspace in AWS S3."""
