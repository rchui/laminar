"""Test conditional branching."""

import pytest

from laminar import Flow, Layer
from laminar.configurations import datastores, executors
from laminar.types import unwrap

flow = Flow(name="Test", datastore=datastores.Memory(), executor=executors.Thread())


@flow.register()
class A(Layer):
    def __call__(self) -> None:
        self.foo = "bar"


@flow.register()
class B(Layer):
    def __call__(self, a: A) -> None:
        self.foo = a.foo

    def __enter__(self) -> bool:
        return False


@flow.register()
class C(Layer):
    def __call__(self, a: A) -> None:
        self.foo = "baz"


@flow.register()
class D(Layer):
    def __call__(self, b: B, c: C) -> None:
        if b.executed:
            self.foo = [b.foo, c.foo]
        else:
            self.foo = [c.foo]

    def __enter__(self) -> bool:
        return True


@pytest.mark.flow
class TestConditionalBranching:
    def test_flow(self) -> None:
        execution = flow()

        results = flow.results(unwrap(execution))

        assert results.layer(A).foo == "bar"
        assert results.layer(B).executed is False
        assert results.layer(C).foo == "baz"
        assert results.layer(D).executed is True
        assert results.layer(D).foo == ["baz"]
