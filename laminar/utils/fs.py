from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, TextIO, Union, overload

import smart_open
from typing_extensions import Literal


@overload
def open(uri: str, mode: Literal["r"]) -> TextIO:
    ...


@overload
def open(uri: str, mode: Literal["rb"]) -> BinaryIO:
    ...


@overload
def open(uri: str, mode: Literal["w"]) -> TextIO:
    ...


@overload
def open(uri: str, mode: Literal["wb"]) -> BinaryIO:
    ...


@contextmanager  # type: ignore
def open(uri: str, mode: Literal["r", "rb", "w", "wb"]) -> Union[BinaryIO, TextIO]:
    """Open a file handler to a local or remote file.

    Usage::

        with fs.open("file:///...", "r") as file: ...
        with fs.open("s3://...", "wb") as file: ...

    Args:
        uri: URI to the file to open.
        mode: Mode to open the file with.

    Returns:
        Union[BinaryIO, TextIO]: File handle to the local/remote file.
    """

    if smart_open.parse_uri(uri).scheme == "file" and "w" in mode:
        Path(uri).parent.mkdir(parents=True, exist_ok=True)

    with smart_open.open(uri, mode) as file:
        yield file


def exists(*, uri: str) -> bool:
    """Check for the existance of a local/remote file.

    Usage::

        fs.exists("file:///...")
        fs.exists("s3://...")

    Args:
        uri: URI to the file to check.

    Returns:
        bool: True if the file exists, else False.
    """

    try:
        with open(uri, "rb"):
            return True
    except IOError:
        return False
