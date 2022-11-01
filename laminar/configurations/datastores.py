"""Configurations for laminar data sources."""

import copy
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, Callable, Dict, Generator, Iterable, List, Tuple, Type, Union, overload

import boto3

from laminar.configurations import serde
from laminar.types import unwrap
from laminar.utils import fs

if TYPE_CHECKING:
    from laminar import Execution, Flow, Layer

DEFAULT_SERDE = serde.PickleProtocol()

ARCHIVE_PATTERN = re.compile(
    r"^.+"  # Greedily match from start
    r"\/(?P<flow>.+?)"  # Match flow name
    r"\/archives"  # Match archive directory
    r"\/(?P<execution>.+?)"  # Match execution id
    r"(?:\/(?P<layer>.+?))?"  # Match layer name
    r"(?:\/(?P<split>\d+?))?"  # Match split index
    r"(?:\/(?P<artifact>.+?)\.json)?$"  # Match artifact name
)


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
    def path(*, layer: "Layer") -> str:
        """Get the path to the Record."""

        return fs.join(layer.execution.flow.name, ".cache", unwrap(layer.execution.id), layer.name, ".record.json")

    def dict(self) -> Dict[str, Any]:
        """Convert the Record to a dict."""

        return asdict(self)

    @staticmethod
    def parse(source: Dict[str, Any]) -> "Record":
        """Get a Record from a dict."""

        return Record(
            flow=Record.FlowRecord(**source["flow"]),
            layer=Record.LayerRecord(**source["layer"]),
            execution=Record.ExecutionRecord(**source["execution"]),
        )


class RecordProtocol(serde.Protocol):
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

    def path(self, *, layer: "Layer") -> str:
        """Get the path to the Artifact."""

        return fs.join(layer.execution.flow.name, "artifacts", f"{self.hexdigest}.gz")

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
    def path(*, layer: "Layer", index: int, name: str, cache: bool = False) -> str:
        """Get the path to the Archive."""

        parts: Tuple[str, ...]

        if cache:
            parts = (layer.execution.flow.name, ".cache", unwrap(layer.execution.id), layer.name, f"{name}.json")
        else:
            parts = (
                layer.execution.flow.name,
                "archives",
                unwrap(layer.execution.id),
                layer.name,
                str(index),
                f"{name}.json",
            )

        return fs.join(*parts)

    def dict(self) -> Dict[str, List[Dict[str, str]]]:
        """Convert the Archive to a dict."""

        return asdict(self)

    @staticmethod
    def parse(source: Dict[str, List[Dict[str, str]]]) -> "Archive":
        """Get an Archive from a dict."""

        return Archive(artifacts=[Artifact(**artifact) for artifact in source["artifacts"]])


class ArchiveProtocol(serde.Protocol):
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
        datastore = self.layer.execution.flow.configuration.datastore

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
            yield self.layer.execution.flow.configuration.datastore.read_artifact(
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
    protocols: Dict[str, serde.Protocol] = field(default_factory=dict)

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

        return fs.join(self.root, path)

    def exists(self, *, path: str) -> bool:
        """Check if a file exists in the datastore.

        Args:
            path: Path from the datastore root to the file.

        Returns:
            True if the file exists else False
        """

        return fs.exists(uri=self.uri(path=path))

    def protocol(self, *dtypes: type) -> Callable[[Type[serde.ProtocolType]], Type[serde.ProtocolType]]:
        """Register a custom serde protocol for a type.

        Usage::

            @datastore.protocol(pd.DataFrame)
            def DataFrameProtocol(serde.Protocol):
                ...
        """

        def decorator(protocol: Type[serde.ProtocolType]) -> Type[serde.ProtocolType]:
            for dtype in dtypes:
                self.protocols[f"{dtype.__module__}.{dtype.__name__}"] = protocol()
            return protocol

        return decorator

    def read_archive(self, *, layer: "Layer", index: int, name: str, cache: bool = False) -> Archive:
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

    def read_artifact(self, *, layer: "Layer", archive: Archive) -> Any:
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

    def read_record(self, *, layer: "Layer") -> Record:
        """Read a layer record from the laminar datastore.

        Args:
            layer: Layer to get the record for.

        Returns:
            Layer record
        """

        record: Record = self._read(uri=self.uri(path=Record.path(layer=layer)), dtype=RecordProtocol.dtype)
        return record

    def _read(self, *, uri: str, dtype: str) -> Any:
        return self.protocols.get(dtype, DEFAULT_SERDE).read(uri)

    def read(self, *, layer: "Layer", index: int, name: str) -> Any:
        """Read from the laminar datastore.

        Args:
            layer: Layer being read from.
            index: Layer index being read from.
            name: Name of the artifact being read.

        Returns:
            Any: Value of the artifact.
        """

        return self.read_artifact(layer=layer, archive=self.read_archive(layer=layer, index=index, name=name))

    def write_archive(self, *, layer: "Layer", name: str, artifacts: List[Artifact], cache: bool = False) -> Archive:
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

    def write_artifact(self, *, layer: "Layer", value: Any) -> Artifact:
        """Write an arifact to the laminar datastore.

        Args:
            layer: Layer being written.
            value: Value of the artifact to write.

        Returns:
            Artifact metadata written to the laminar datastore.
        """

        serializer = self.protocols.get(type(value).__name__, DEFAULT_SERDE)
        artifact = Artifact(dtype=serde.dtype(type(value)), hexdigest=serializer.hexdigest(value))
        self._write(value=value, uri=self.uri(path=artifact.path(layer=layer)), dtype=artifact.dtype)

        return artifact

    def write_record(self, *, layer: "Layer", record: Record) -> None:
        """Write a layer record to the laminar datastore.

        Args:
            layer: Layer the record is for.
            record: Record to write.
        """

        self._write(value=record, uri=self.uri(path=record.path(layer=layer)), dtype=RecordProtocol.dtype)

    def _write(self, *, value: Any, uri: str, dtype: str) -> None:
        self.protocols.get(dtype, DEFAULT_SERDE).write(value, uri)

    def write(self, *, layer: "Layer", name: str, values: Iterable[Any]) -> None:
        """Write to the laminar datastore.

        Args:
            layer: Layer being written to.
            name: Name of the artifact being written.
            values : Artifact values to store.
        """

        artifacts = [self.write_artifact(layer=layer, value=value) for value in values]
        self.write_archive(layer=layer, name=name, artifacts=artifacts)

    def list_executions(self, *, flow: "Flow") -> List["Execution"]:
        """List all executions.

        Args:
            flow: Flow to list executions for.

        Returns:
            All executions.
        """

        executions = sorted(set(self._list(prefix=self.uri(path=fs.join(flow.name, "archives")), group="execution")))
        return [copy.deepcopy(flow).execution(execution) for execution in executions]

    def list_layers(self, *, execution: "Execution") -> List["Layer"]:
        """List all layers in an execution.

        Args:
            execution: Execution to list layers for.

        Returns:
            All layers.
        """

        layers = sorted(
            set(
                self._list(
                    prefix=self.uri(path=fs.join(execution.flow.name, "archives", unwrap(execution.id))), group="layer"
                )
            )
        )
        return [execution.layer(layer) for layer in layers]

    def list_artifacts(self, *, layer: "Layer") -> List[str]:
        """List all artifacts in a layer execution.

        Args:
            layer: Layer to list artifacts for.

        Returns:
            All artifacts.
        """

        return sorted(
            set(
                self._list(
                    prefix=self.uri(
                        path=fs.join(layer.execution.flow.name, "archives", unwrap(layer.execution.id), layer.name, "0")
                    ),
                    group="artifact",
                )
            )
        )

    def _list(self, *, prefix: str, group: str) -> Iterable[str]:
        raise NotImplementedError


@dataclass(frozen=True)
class Local(DataStore):
    """Store the laminar workspace on the local filesystem.

    Usage::

        Flow(datastore=Local())
    """

    root: str = str(Path.cwd() / ".laminar")

    def _list(self, *, prefix: str, group: str) -> Iterable[str]:
        for path in map(str, Path(prefix).glob("*")):
            match = ARCHIVE_PATTERN.match(path)
            if match is not None:
                yield match.group(group)


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

    def _list(self, *, prefix: str, group: str) -> Iterable[str]:
        for path in self.cache:
            if path.startswith(prefix):
                match = ARCHIVE_PATTERN.match(path)
                if match is not None:
                    yield match.group(group)


class AWS:
    @dataclass(frozen=True)
    class S3(DataStore):
        """Store the laminar workspace in AWS S3.

        Usage::

            Flow(datastore=AWS.S3())
        """

        def _list(self, *, prefix: str, group: str) -> Iterable[str]:
            parts = fs.parse_uri(prefix)

            s3 = boto3.resource("s3")
            bucket = s3.Bucket(name=parts.bucket)
            for response in bucket.objects.filter(Prefix=parts.key_id):
                match = ARCHIVE_PATTERN.match(response.key)
                if match is not None:
                    yield match.group(group)
