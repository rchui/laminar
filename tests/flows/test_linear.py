"""Test linear flows."""

import pytest

from laminar import Flow, Layer
from laminar.configurations import datastores, executors

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
def test_flow() -> None:
    execution = flow()

    assert execution.layer(A).foo == "bar"
    assert execution.layer(B).foo == "bar"
    assert execution.layer(C).foo == "bar"
