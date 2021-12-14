"""Configurations for laminar data sources."""

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, Callable, Dict, Generator, Iterable, List, Tuple, Type, Union, overload

from dacite.core import from_dict

from laminar.configurations import serde
from laminar.types import unwrap
from laminar.utils import fs

if TYPE_CHECKING:
    from laminar import Layer
else:
    Layer = "Layer"

DEFAULT_SERDE = serde.PickleProtocol()


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


class RecordProtocol(serde.Protocol[Record]):
    """Custom protocol for serializing Records."""

    def load(self, file: BinaryIO) -> Record:
        return Record.parse(json.load(file))

    def dumps(self, value: Record) -> bytes:
        return json.dumps(value.dict()).encode()


@dataclass(frozen=True)
class Artifact:
    """Handler for artifacts in the laminar datastore.

    Notes:
        Artifacts are gziped, pickled layer instance attributes.
    """

    #: Data type of the artifact.
    dtype: str
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


class ArchiveProtocol(serde.Protocol[Archive]):
    """Custom protocol for serializing Archives."""

    def load(self, file: BinaryIO) -> Archive:
        return Archive.parse(json.load(file))

    def dumps(self, value: Archive) -> bytes:
        return json.dumps(value.dict()).encode()


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
            yield self.layer.flow.configuration.datastore.read_artifact(
                layer=self.layer, archive=Archive(artifacts=[artifact])
            )

    def __len__(self) -> int:
        return len(self.archive)


@dataclass(frozen=True)
class DataStore:
    """Base flow datastore."""

    #: URI root of the datastore
    root: str
    #: Internal datastore cache
    cache: Dict[str, Any] = field(default_factory=dict)
    #: Custom serde protocols for reading/writing artifacts
    protocols: Dict[str, serde.Protocol[Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.root.endswith(("://", ":///")):
            object.__setattr__(self, "root", self.root.rstrip("/"))

        self.protocols[ArchiveProtocol.dtype] = ArchiveProtocol()
        self.protocols[RecordProtocol.dtype] = RecordProtocol()

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

    def serde(self, dtype: type) -> Callable[[Type[serde.ProtocolType]], Type[serde.ProtocolType]]:
        """Register a custom serde protocol for a type.

        Usage::

            @datastore.protocol(pd.DataFrame)
            def DataFrameProtocol(serde.Protocol):
                ...
        """

        def decorator(protocol: Type[serde.ProtocolType]) -> Type[serde.ProtocolType]:
            self.protocols[f"{dtype.__module__}.{dtype.__name__}"] = protocol()
            return protocol

        return decorator

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

        archive: Archive = self._read(
            uri=self.uri(path=Archive.path(layer=layer, index=index, name=name, cache=cache)),
            dtype=ArchiveProtocol.dtype,
        )
        return archive

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
            artifact = archive.artifacts[0]
            return self._read(uri=self.uri(path=artifact.path(layer=layer)), dtype=artifact.dtype)

        # Create an accessor for the artifacts
        else:
            return Accessor(archive=archive, layer=layer)

    def _read(self, *, uri: str, dtype: str) -> Any:
        return self.protocols.get(dtype, DEFAULT_SERDE).read(uri)

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
        self._write(
            value=archive,
            uri=self.uri(path=archive.path(layer=layer, index=unwrap(layer.index, 0), name=name, cache=cache)),
            dtype=ArchiveProtocol.dtype,
        )
        return archive

    def write_artifact(self, *, layer: Layer, value: Any) -> Artifact:
        """Write an arifact to the laminar datastore.

        Args:
            layer: Layer being written.
            value: Value of the artifact to write.

        Returns:
            Artifact metadata written to the laminar datastore.
        """

        serializer = self.protocols.get(type(value).__name__, DEFAULT_SERDE)
        artifact = Artifact(
            dtype=serde.dtype(type(value)), hexdigest=hashlib.sha256(serializer.dumps(value)).hexdigest()
        )
        self._write(value=value, uri=self.uri(path=artifact.path(layer=layer)), dtype=artifact.dtype)

        return artifact

    def _write(self, *, value: Any, uri: str, dtype: str) -> None:
        self.protocols.get(dtype, DEFAULT_SERDE).write(value, uri)

    def write(self, *, layer: Layer, name: str, values: Iterable[Any]) -> None:
        """Write to the laminar datastore.

        Args:
            layer: Layer being written to.
            name: Name of the artifact being written.
            values : Artifact values to store.
        """

        artifacts = [self.write_artifact(layer=layer, value=value) for value in values]
        self.write_archive(layer=layer, name=name, artifacts=artifacts)

    def read_record(self, *, layer: Layer) -> Record:
        """Read a layer record from the laminar datastore.

        Args:
            layer: Layer to get the record for.

        Returns:
            Layer record
        """

        record: Record = self._read(uri=self.uri(path=Record.path(layer=layer)), dtype=RecordProtocol.dtype)
        return record

    def write_record(self, *, layer: Layer, record: Record) -> None:
        """Write a layer record to the laminar datastore.

        Args:
            layer: Layer the record is for.
            record: Record to write.
        """

        self._write(value=record, uri=self.uri(path=record.path(layer=layer)), dtype=RecordProtocol.dtype)


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

    def _read(self, *, uri: str, dtype: str) -> Any:
        return self.cache[uri]

    def _write(self, *, value: Any, uri: str, dtype: str) -> None:
        self.cache[uri] = value


class AWS:
    @dataclass(frozen=True)
    class S3(DataStore):
        """Store the laminar workspace in AWS S3.

        Usage::

            Flow(datastore=AWS.S3())
        """
