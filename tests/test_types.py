"""Unit tests for laminar.types"""

import pytest

from laminar import types
from laminar.configurations.datastores import Accessor, Archive


class TestAnnotations:
    def test_builtins(self) -> None:
        def test(a: str, b: bool, c: int) -> None:
            ...

        assert types.annotations(test) == (str, bool, int)

    def test_custom(self) -> None:
        def test(a: Accessor, b: Archive) -> None:
            ...

        assert types.annotations(test) == (Accessor, Archive)

    def test_forward_reference(self) -> None:
        def test(a: "Test") -> None:
            ...

        assert types.annotations(test) == (Test,)


class Test:
    ...


class TestUnwrap:
    def test_wrapped(self) -> None:
        assert types.unwrap(1) == 1

    def test_none(self) -> None:
        with pytest.raises(ValueError):
            assert types.unwrap(None)
