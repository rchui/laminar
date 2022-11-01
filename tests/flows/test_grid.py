"""Test foreach flows."""

from typing import List, Tuple

import pytest

from laminar import Flow, Layer
from laminar.configurations import datastores, executors
from laminar.configurations.layers import ForEach, Parameter


class SingleGridFlow(Flow):
    ...


@SingleGridFlow.register
class A(Layer):
    foo: List[int]
    bar: List[str]

    def __call__(self) -> None:
        self.shard(foo=[1, 2, 3])
        self.shard(bar=["a", "b"])


@SingleGridFlow.register(
    foreach=ForEach(parameters=[Parameter(layer=A, attribute="foo"), Parameter(layer=A, attribute="bar")])
)
class B(Layer):
    result: List[Tuple[str, int]]

    def __call__(self, a: A) -> None:
        self.result = (a.bar, a.foo)  # type: ignore


@SingleGridFlow.register
class C(Layer):
    def __call__(self, b: B) -> None:
        self.result = list(b.result)


@pytest.mark.flow
def test_grid() -> None:
    flow = SingleGridFlow(datastore=datastores.Memory(), executor=executors.Thread())
    execution = flow()

    assert list(execution.layer(A).foo) == [1, 2, 3]
    assert list(execution.layer(A).bar) == ["a", "b"]
    assert list(execution.layer(B).result) == [("a", 1), ("b", 1), ("a", 2), ("b", 2), ("a", 3), ("b", 3)]
    assert execution.layer(C).result == [("a", 1), ("b", 1), ("a", 2), ("b", 2), ("a", 3), ("b", 3)]


class MultiGridFlow(Flow):
    ...


@MultiGridFlow.register
class A12(Layer):
    foo: List[int]

    def __call__(self) -> None:
        self.shard(foo=[1, 2, 3])


@MultiGridFlow.register
class A22(Layer):
    bar: List[str]

    def __call__(self) -> None:
        self.shard(bar=["a", "b"])


@MultiGridFlow.register(
    foreach=ForEach(parameters=[Parameter(layer=A12, attribute="foo"), Parameter(layer=A22, attribute="bar")])
)
class B2(Layer):
    result: List[Tuple[str, int]]

    def __call__(self, a12: A12, a22: A22) -> None:
        self.result = (a22.bar, a12.foo)  # type: ignore


@MultiGridFlow.register
class C2(Layer):
    def __call__(self, b: B2) -> None:
        self.result = list(b.result)


@pytest.mark.flow
def test_double_grid() -> None:
    flow2 = MultiGridFlow(datastore=datastores.Memory(), executor=executors.Thread())
    execution = flow2()

    assert list(execution.layer(A12).foo) == [1, 2, 3]
    assert list(execution.layer(A22).bar) == ["a", "b"]
    assert list(execution.layer(B2).result) == [("a", 1), ("b", 1), ("a", 2), ("b", 2), ("a", 3), ("b", 3)]
    assert execution.layer(C2).result == [("a", 1), ("b", 1), ("a", 2), ("b", 2), ("a", 3), ("b", 3)]
