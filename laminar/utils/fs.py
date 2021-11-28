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
    if smart_open.parse_uri(uri).scheme == "file" and "w" in mode:
        Path(uri).parent.mkdir(parents=True, exist_ok=True)

    with smart_open.open(uri, mode) as file:
        yield file
