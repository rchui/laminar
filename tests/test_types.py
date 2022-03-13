"""Unit tests for laminar.types"""

import pytest

from laminar import Flow, Layer, types

flow = Flow(name="HintFlow")


@flow.register()
class Ref(Layer):
    ...


class TestHints:
    def test_reference(self) -> None:
        def test(a: "Ref") -> None:
            ...

        assert types.hints(flow, test) == (Ref(flow=flow),)

    def test_forward_reference(self) -> None:
        def test(a: "ForwardRef") -> None:
            ...

        assert types.hints(flow, test) == (ForwardRef(flow=flow),)


@flow.register()
class ForwardRef(Layer):
    ...


class TestUnwrap:
    def test_wrapped(self) -> None:
        assert types.unwrap(1) == 1

    def test_none(self) -> None:
        with pytest.raises(ValueError):
            assert types.unwrap(None)
