"""Test parameterized flows."""

import pytest

from laminar import Flow, Layer
from laminar.components import Parameters
from laminar.configurations import datastores, executors

flow = Flow(name="Test", datastore=datastores.Memory(), executor=executors.Thread())


@flow.register()
class A(Layer):
    def __call__(self, parameters: Parameters) -> None:
        self.foo = parameters.foo


@pytest.mark.flow
class TestParameter:
    def test_flow(self) -> None:
        execution = flow.parameters(foo="bar")
        flow(execution=execution)

        results = flow.execution(execution)

        assert results.layer(Parameters).foo == "bar"
        assert results.layer(A).foo == "bar"
