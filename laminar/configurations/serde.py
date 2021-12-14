"""Configurations for laminar serde."""

from typing import Any, BinaryIO, Generic, TypeVar

import cloudpickle

from laminar.utils import fs

T = TypeVar("T")


def dtype(cls: type) -> str:
    """Get the serde dtype name given a class type."""

    return f"{cls.__module__}.{cls.__name__}"


class ProtocolMeta(type):
    @property
    def dtype(cls) -> str:
        return dtype(cls)


class Protocol(Generic[T], metaclass=ProtocolMeta):
    """Generic base class for defining ser(de) protocols."""

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{key}={value}' for key, value in vars(self).items()])})"

    def read(self, uri: str) -> T:
        """Read a value from a URI with a custom protocol.

        Args:
            uri: URI to read from.

        Returns:
            Value from the URI.
        """

        with fs.open(uri, "rb") as file:
            return self.load(file)

    def load(self, file: BinaryIO) -> T:
        """Deserialize a value from a file.

        Usage::

            with open(..., "rb") as file:
                Protocol().load(file)

        Args:
            file: File handler to read from.

        Returns:
            Deserialized value.
        """

        return self.loads(file.read())

    def loads(self, stream: bytes) -> T:
        """Deserialize a value from a byte stream.

        Usage::

            Protocol().loads(...)

        Args:
            stream: Bytes to deserialize

        Returns:
            Deserialized value.
        """

        raise NotImplementedError

    def write(self, value: T, uri: str) -> None:
        """Write a value to a URI with a custom protocol.

        Args:
            value: Value to write to the URI.
            uri: URI to write to.
        """

        with fs.open(uri, "wb") as file:
            self.dump(value, file)

    def dump(self, value: T, file: BinaryIO) -> None:
        """Serialize a value to a file.

        Usage::

            with open(..., "wb") as file:
                Protocol().dump(..., file)

        Args:
            value: Value to serialize.
            file: File handler to write to.
        """

        file.write(self.dumps(value))

    def dumps(self, value: T) -> bytes:
        """Serialize a value to a byte string.

        Usage::

            Protocol.dumps(...)

        Args:
            value: Value to serialize.

        Returns:
            Serialized value.
        """

        raise NotImplementedError


ProtocolType = TypeVar("ProtocolType", bound=Protocol[Any])


class PickleProtocol(Protocol[Any]):
    """Custom protocol for serializing Python objects using pickle."""

    def load(self, file: BinaryIO) -> Any:
        return cloudpickle.load(file)

    def loads(self, stream: bytes) -> Any:
        return cloudpickle.loads(stream)

    def dump(self, value: Any, file: BinaryIO) -> None:
        cloudpickle.dump(value, file)

    def dumps(self, value: Any) -> bytes:
        stream: bytes = cloudpickle.dumps(value)
        return stream
