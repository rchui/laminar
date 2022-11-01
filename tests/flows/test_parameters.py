"""Test parameterized flows."""

import pytest

from laminar import Flow, Layer
from laminar.components import Parameters
from laminar.configurations import datastores, executors


class ParameterFlow(Flow):
    ...


@ParameterFlow.register
class A(Layer):
    foo: str

    def __call__(self, parameters: Parameters) -> None:
        self.foo = parameters.foo


@pytest.mark.flow
def test_flow() -> None:
    flow = ParameterFlow(datastore=datastores.Memory(), executor=executors.Thread())
    execution = flow(foo="bar")

    assert execution.layer(Parameters).foo == "bar"
    assert execution.layer(A).foo == "bar"
