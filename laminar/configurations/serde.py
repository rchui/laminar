"""Configurations for laminar serde."""

from typing import Any, BinaryIO, Generic, TypeVar

T = TypeVar("T")


class Protocol(Generic[T]):
    """Generic base class for defining ser(de) protocols."""

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

        raise NotImplementedError

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

    def dump(self, value: T, file: BinaryIO) -> None:
        """Serialize a value to a file.

        Usage::

            with open(..., "wb") as file:
                Protocol().dump(..., file)

        Args:
            value: Value to serialize.
            file: File handler to write to.
        """

        raise NotImplementedError

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
