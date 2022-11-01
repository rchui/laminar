"""Configurations for laminar serde."""

import hashlib
from typing import Any, BinaryIO, TypeVar

import cloudpickle

from laminar.utils import fs, stringify


def dtype(cls: type) -> str:
    """Get the serde dtype name given a class type."""

    return f"{cls.__module__}.{cls.__name__}"


class MetaProtocol(type):
    @property
    def dtype(cls) -> str:
        return dtype(cls)


class Protocol(metaclass=MetaProtocol):
    """Generic base class for defining ser(de) protocols."""

    def __repr__(self) -> str:
        return stringify(self, type(self).__name__)

    def read(self, uri: str) -> Any:
        """Read a value from a URI with a custom protocol.

        Args:
            uri: URI to read from.

        Returns:
            Value from the URI.
        """

        with fs.open(uri, "rb") as file:
            return self.load(file)

    def load(self, file: BinaryIO) -> Any:
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

    def loads(self, stream: bytes) -> Any:
        """Deserialize a value from a byte stream.

        Usage::

            Protocol().loads(...)

        Args:
            stream: Bytes to deserialize

        Returns:
            Deserialized value.
        """

        raise NotImplementedError

    def write(self, value: Any, uri: str) -> None:
        """Write a value to a URI with a custom protocol.

        Args:
            value: Value to write to the URI.
            uri: URI to write to.
        """

        with fs.open(uri, "wb") as file:
            self.dump(value, file)

    def dump(self, value: Any, file: BinaryIO) -> None:
        """Serialize a value to a file.

        Usage::

            with open(..., "wb") as file:
                Protocol().dump(..., file)

        Args:
            value: Value to serialize.
            file: File handler to write to.
        """

        file.write(self.dumps(value))

    def dumps(self, value: Any) -> bytes:
        """Serialize a value to a byte string.

        Usage::

            Protocol.dumps(...)

        Args:
            value: Value to serialize.

        Returns:
            Serialized value.
        """

        raise NotImplementedError

    def hexdigest(self, value: Any) -> str:
        """Compute the hexdigest to generate the content address.

        Args:
            value: Value to compute hexdigest from.

        Returns:
            Hexdigest to use as the content address.
        """

        return hashlib.sha256(self.dumps(value)).hexdigest()


ProtocolType = TypeVar("ProtocolType", bound=Protocol)


class PickleProtocol(Protocol):
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
