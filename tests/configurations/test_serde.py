"""Unit tests for laminar.configurations.protocol"""

from laminar.configurations import serde


class TestDtype:
    def test_builtin(self) -> None:
        assert serde.dtype(str) == "builtins.str"

    def test_custom(self) -> None:
        assert serde.dtype(serde.Protocol) == "laminar.configurations.serde.Protocol"
