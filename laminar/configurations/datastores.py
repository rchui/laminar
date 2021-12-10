"""Configurations for laminar data sources."""

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Generator, Iterable, List, Tuple, Union, overload

import cloudpickle
from dacite.core import from_dict

from laminar.utils import fs, unwrap

if TYPE_CHECKING:
    from laminar import Layer
else:
    Layer = "Layer"


@dataclass(frozen=True)
class Record:
    """Handler for metadata about how a Layer was executed."""

    @dataclass(frozen=True)
    class FlowRecord:
        #: Name of the flow
        name: str

    @dataclass(frozen=True)
    class LayerRecord:
        #: Name of the layer
        name: str

    @dataclass(frozen=True)
    class ExecutionRecord:
        #: Number of splits in the layer
        splits: int

    #: Flow record information
    flow: FlowRecord
    #: Layer record information
    layer: LayerRecord
    #: Execution record information
    execution: ExecutionRecord

    @staticmethod
    def path(*, layer: Layer) -> str:
        """Get the path to the Record."""

        return os.path.join(layer.flow.name, ".cache", unwrap(layer.flow.execution), layer.name, ".record.json")

    def dict(self) -> Dict[str, Any]:
        """Convert the Record to a dict."""

        return asdict(self)

    @staticmethod
    def parse(source: Dict[str, Any]) -> "Record":
        """Get a Record from a dict."""

        return from_dict(Record, source)


@dataclass(frozen=True)
class Artifact:
    """Handler for artifacts in the laminar datastore.

    Notes:
        Artifacts are gziped, pickled layer instance attributes.
    """

    #: SHA256 hexdigest of the artifact bytes.
    hexdigest: str

    def path(self, *, layer: Layer) -> str:
        """Get the path to the Artifact."""

        return os.path.join(layer.flow.name, "artifacts", f"{self.hexdigest}.gz")

    def dict(self) -> Dict[str, str]:
        """Convert the Artifact to a dict."""

        return asdict(self)


@dataclass(frozen=True)
class Archive:
    """Handler for archives in the laminar datastore.

    Notes:
        Archives are metadata for artifacts.
    """

    artifacts: List[Artifact]

    def __len__(self) -> int:
        return len(self.artifacts)

    @staticmethod
    def path(*, layer: Layer, index: int, name: str, cache: bool = False) -> str:
        """Get the path to the Archive."""

        parts: Tuple[str, ...]

        if cache:
            parts = (layer.flow.name, ".cache", unwrap(layer.flow.execution), layer.name, f"{name}.json")
        else:
            parts = (layer.flow.name, "archives", unwrap(layer.flow.execution), layer.name, str(index), f"{name}.json")

        return os.path.join(*parts)

    def dict(self) -> Dict[str, List[Dict[str, str]]]:
        """Convert the Archive to a dict."""

        return asdict(self)

    @staticmethod
    def parse(source: Dict[str, List[Dict[str, str]]]) -> "Archive":
        """Get an Archive from a dict."""

        return from_dict(Archive, source)


@dataclass(frozen=True)
class Accessor:
    """Artifact handler for sharded artifacts."""

    #: Archive the accessor is reading from
    archive: Archive
    #: Layer to read the archive with
    layer: "Layer"

    @overload
    def __getitem__(self, key: int) -> Any:
        ...

    @overload
    def __getitem__(self, key: slice) -> List[Any]:
        ...

    def __getitem__(self, key: Union[int, slice]) -> Any:
        datastore = self.layer.flow.configuration.datastore

        # Directly access an index
        if isinstance(key, int):
            if key >= len(self.archive):
                raise IndexError

            return datastore.read_artifact(layer=self.layer, archive=Archive(artifacts=[self.archive.artifacts[key]]))

        # Slicing for multiple splits
        elif isinstance(key, slice):
            return [
                datastore.read_artifact(layer=self.layer, archive=Archive(artifacts=[artifact]))
                for artifact in self.archive.artifacts[key]
            ]

        else:
            raise TypeError(f"{type(key)} is not a valid key type for Accessor.__getitem__")

    def __iter__(self) -> Generator[Any, None, None]:
        for artifact in self.archive.artifacts:
            yield self.layer.flow.configuration.datastore._read_artifact(path=artifact.path(layer=self.layer))

    def __len__(self) -> int:
        return len(self.archive)


@dataclass(frozen=True)
class DataStore:
    """Base flow datastore."""

    #: URI root of the datastore
    root: str
    #: Internal datastore cache
    cache: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.root.endswith(("://", ":///")):
            object.__setattr__(self, "root", self.root.rstrip("/"))

    def uri(self, *, path: str) -> str:
        """Given a path, generate a URI in the datastore.

        Args:
            path: Path relative to the datastore root.

        Returns:
            URI to a location in the datastore.
        """

        return os.path.join(self.root, path)

    def exists(self, *, path: str) -> bool:
        """Check if a file exists in the datastore.

        Args:
            path: Path from the datastore root to the file.

        Returns:
            True if the file exists else False
        """

        return fs.exists(uri=self.uri(path=path))

    def _read_archive(self, *, path: str) -> Archive:
        with fs.open(self.uri(path=path), "r") as file:
            return Archive.parse(json.load(file))

    def read_archive(self, *, layer: Layer, index: int, name: str, cache: bool = False) -> Archive:
        """Read an archive from the laminar datastore.

        Args:
            layer: Layer being read from.
            index: Layer index being read from.
            name: Name of the artifact the archive is for.
            cache: Read the archive from the cache.

        Returns:
            Archive: Archive of the requested artifact.
        """

        return self._read_archive(path=Archive.path(layer=layer, index=index, name=name, cache=cache))

    def _read_artifact(self, *, path: str) -> Any:
        with fs.open(self.uri(path=path), "rb") as file:
            return cloudpickle.load(file)

    def read_artifact(self, *, layer: Layer, archive: Archive) -> Any:
        """Read an artifact form the laminar datastore.

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
        """Read from the laminar datastore.

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
            json.dump(archive.dict(), file)

    def write_archive(self, *, layer: Layer, name: str, artifacts: List[Artifact], cache: bool = False) -> Archive:
        """Write an archive to the laminar datastore.

        Args:
            layer: Layer being written.
            name: Name of the archive being written.
            artifacts: Artfacts associated with the archive.
            cache: Write the archive to the cache.

        Returns:
            Archive metadata written to the laminar datastore.
        """

        archive = Archive(artifacts=artifacts)
        self._write_archive(
            path=archive.path(layer=layer, index=unwrap(layer.index, 0), name=name, cache=cache), archive=archive
        )

        return archive

    def _write_artifact(self, *, path: str, value: Any) -> None:
        with fs.open(self.uri(path=path), "wb") as file:
            cloudpickle.dump(value, file)

    def write_artifact(self, *, layer: Layer, value: Any) -> Artifact:
        """Write an arifact to the laminar datastore.

        Args:
            layer: Layer being written.
            value: Value of the artifact to write.

        Returns:
            Artifact metadata written to the laminar datastore.
        """

        artifact = Artifact(hexdigest=hashlib.sha256(cloudpickle.dumps(value)).hexdigest())
        self._write_artifact(path=artifact.path(layer=layer), value=value)

        return artifact

    def write(self, *, layer: Layer, name: str, values: Iterable[Any]) -> None:
        """Write to the laminar datastore.

        Args:
            layer: Layer being written to.
            name: Name of the artifact being written.
            values : Artifact values to store.
        """

        artifacts = [self.write_artifact(layer=layer, value=value) for value in values]
        self.write_archive(layer=layer, name=name, artifacts=artifacts)

    def _read_record(self, *, path: str) -> Record:
        with fs.open(self.uri(path=path), "r") as file:
            return Record.parse(json.load(file))

    def read_record(self, *, layer: Layer) -> Record:
        """Read a layer record from the laminar datastore.

        Args:
            layer: Layer to get the record for.

        Returns:
            Layer record
        """

        return self._read_record(path=Record.path(layer=layer))

    def _write_record(self, *, path: str, record: Record) -> None:
        with fs.open(self.uri(path=path), "w") as file:
            json.dump(record.dict(), file)

    def write_record(self, *, layer: Layer, record: Record) -> None:
        """Write a layer record to the laminar datastore.

        Args:
            layer: Layer the record is for.
            record: Record to write.
        """

        return self._write_record(path=record.path(layer=layer), record=record)


@dataclass(frozen=True)
class Local(DataStore):
    """Store the laminar workspace on the local filesystem.

    Usage::

        Flow(datastore=Local())
    """

    root: str = str(Path.cwd() / ".laminar")


@dataclass(frozen=True)
class Memory(DataStore):
    """Store the laminar workspace in memory.

    Usage::

        Flow(datastore=Memory())
    """

    root: str = "memory:///"

    def exists(self, *, path: str) -> bool:
        return self.uri(path=path) in self.cache

    def _read_archive(self, *, path: str) -> Archive:
        return self.cache[self.uri(path=path)]

    def _write_archive(self, *, path: str, archive: Archive) -> None:
        self.cache[self.uri(path=path)] = archive

    def _read_artifact(self, *, path: str) -> Any:
        return self.cache[self.uri(path=path)]

    def _write_artifact(self, *, path: str, value: Any) -> None:
        self.cache[self.uri(path=path)] = value

    def _read_record(self, *, path: str) -> Record:
        return self.cache[self.uri(path=path)]

    def _write_record(self, *, path: str, record: Record) -> None:
        self.cache[self.uri(path=path)] = record


class AWS:
    @dataclass(frozen=True)
    class S3(DataStore):
        """Store the laminar workspace in AWS S3.

        Usage::

            Flow(datastore=AWS.S3())
        """
