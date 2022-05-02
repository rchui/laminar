"""Test composed flows."""

import pytest

from laminar import Flow, Layer
from laminar.components import Parameters
from laminar.configurations import datastores, executors
from laminar.types import unwrap


class Flow1(Flow):
    ...


@Flow1.register()
class A(Layer):
    def __call__(self) -> None:
        self.foo = "bar"


class Flow2(Flow):
    ...


@Flow2.register()
class B(Layer):
    def __call__(self, parameters: Parameters) -> None:
        self.foo = parameters.foo


class Flow3(Flow):
    ...


@Flow3.register()
class C(Layer):
    def __call__(self, parameters: Parameters) -> None:
        self.foo = parameters.foo


@pytest.mark.flow
def test_flow() -> None:
    flow1 = Flow1(datastore=datastores.Memory(), executor=executors.Thread())
    flow2 = Flow2(datastore=datastores.Memory(), executor=executors.Thread())
    flow3 = Flow3(datastore=datastores.Memory(), executor=executors.Thread())

    execution = (
        flow1()
        .chain(flow=flow2, linker=lambda execution: Parameters(foo=execution.layer(A).foo))
        .chain(flow=flow3, linker=lambda execution: Parameters(foo=execution.layer(B).foo))
    )

    assert flow2.execution(unwrap(execution.id)).layer(B).foo == "bar"
    assert flow3.execution(unwrap(execution.id)).layer(C).foo == "bar"


class CombinedFlow(Flow1, Flow2, Flow3):
    ...


@pytest.mark.flow
def test_combination() -> None:
    assert sorted(CombinedFlow.registry) == ["A", "B", "C", "Parameters"]
    assert CombinedFlow.registry["A"] == A()
    assert CombinedFlow.registry["B"] == B()
    assert CombinedFlow.registry["C"] == C()

    flow = CombinedFlow(datastore=datastores.Memory(), executor=executors.Thread())
    execution = flow(foo="bar")

    assert flow.execution(unwrap(execution.id)).layer(B).foo == "bar"
    assert flow.execution(unwrap(execution.id)).layer(C).foo == "bar"
