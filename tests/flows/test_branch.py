"""Test branching flows."""

import pytest

from laminar import Flow, Layer
from laminar.configurations import datastores, executors


class BranchFlow(Flow): ...


@BranchFlow.register
class A(Layer):
    def __call__(self) -> None:
        self.foo = "bar"


@BranchFlow.register
class B(Layer):
    def __call__(self, a: A) -> None:
        self.foo = a.foo


@BranchFlow.register
class C(Layer):
    def __call__(self, a: A) -> None:
        self.foo = "baz"


@BranchFlow.register
class D(Layer):
    def __call__(self, b: B, c: C) -> None:
        self.foo = [b.foo, c.foo]


@pytest.mark.flow
def test_flow() -> None:
    flow = BranchFlow(datastore=datastores.Memory(), executor=executors.Thread())
    execution = flow()

    assert execution.layer(A).foo == "bar"
    assert execution.layer(B).foo == "bar"
    assert execution.layer(C).foo == "baz"
    assert execution.layer(D).foo == ["bar", "baz"]
