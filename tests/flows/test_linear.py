"""Test linear flows."""

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


@flow.register()
class C(Layer):
    def __call__(self, b: B) -> None:
        self.foo = b.foo


@pytest.mark.flow
class TestLinear:
    def test_flow(self) -> None:
        execution = flow()

        results = flow.execution(unwrap(execution))

        assert results.layer(A).foo == "bar"
        assert results.layer(B).foo == "bar"
        assert results.layer(C).foo == "bar"
