"""Unit tests for laminar.utils.fs"""

from pathlib import Path

from laminar.utils import fs


def test_exists() -> None:
    assert fs.exists(uri=str(Path(__file__).resolve()))
    assert not fs.exists(uri=str(Path(__file__).resolve() / "foo.bar"))
