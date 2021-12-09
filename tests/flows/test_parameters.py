"""Test parameterized flows."""

import pytest

from laminar import Flow, Layer
from laminar.components import Parameters
from laminar.configurations import datastores, executors
from laminar.utils import unwrap

flow = Flow(name="Test", datastore=datastores.Memory(), executor=executors.Thread())


@flow.register()
class A(Layer):
    def __call__(self, parameters: Parameters) -> None:
        self.foo = parameters.foo


@pytest.mark.flow
class TestParameter:
    def test_flow(self) -> None:
        execution = flow(foo="bar")

        results = flow.results(unwrap(execution))

        assert results.layer(A).foo == "bar"
