"""Test parameterized flows."""

import pytest

from laminar import Flow, Layer
from laminar.components import Parameters
from laminar.configurations import datastores, executors
from laminar.types import unwrap

flow = Flow(name="Test", datastore=datastores.Memory(), executor=executors.Thread())


@flow.register()
class A(Layer):
    foo: str

    def __call__(self, parameters: Parameters) -> None:
        self.foo = parameters.foo


@pytest.mark.flow
class TestParameter:
    def test_flow(self) -> None:
        execution_id = flow(foo="bar")

        execution = flow.execution(unwrap(execution_id))

        assert execution.layer(Parameters).foo == "bar"
        assert execution.layer(A).foo == "bar"
