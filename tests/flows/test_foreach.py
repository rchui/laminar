"""Test foreach flows."""

from typing import List, cast

import pytest

from laminar import Flow, Layer
from laminar.configurations import datastores, executors
from laminar.configurations.layers import ForEach, Parameter
from laminar.types import unwrap


class ForeachFlow(Flow):
    ...


@ForeachFlow.register()
class A(Layer):
    foo: List[int]

    def __call__(self) -> None:
        self.shard(foo=[1, 2, 3])


@ForeachFlow.register(foreach=ForEach(parameters=[Parameter(layer=A, attribute="foo")]))
class B(Layer):
    foo: List[int]

    def __call__(self, a: A) -> None:
        self.foo = cast(List[int], cast(int, a.foo) + unwrap(self.index) ** 2)


@ForeachFlow.register()
class C(Layer):
    def __call__(self, b: B) -> None:
        self.foo = [value + i for i, value in enumerate(b.foo)]


@pytest.mark.flow
def test_flow() -> None:
    flow = ForeachFlow(datastore=datastores.Memory(), executor=executors.Thread())
    execution = flow()

    assert list(execution.layer(A).foo) == [1, 2, 3]
    assert list(execution.layer(B).foo) == [1, 3, 7]
    assert execution.layer(C).foo == [1, 4, 9]
