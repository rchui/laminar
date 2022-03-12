"""Test foreach flows."""

from typing import List, Tuple

import pytest

from laminar import Flow, Layer
from laminar.configurations import datastores, executors
from laminar.configurations.layers import ForEach, Parameter
from laminar.types import unwrap

flow = Flow(name="Test", datastore=datastores.Memory(), executor=executors.Thread())


@flow.register()
class A(Layer):
    foo: List[int]
    bar: List[str]

    def __call__(self) -> None:
        self.shard(foo=[1, 2, 3])
        self.shard(bar=["a", "b"])


@flow.register(foreach=ForEach(parameters=[Parameter(layer=A, attribute="foo"), Parameter(layer=A, attribute="bar")]))
class B(Layer):
    result: List[Tuple[str, int]]

    def __call__(self, a: A) -> None:
        self.result = (a.bar, a.foo)  # type: ignore


@flow.register()
class C(Layer):
    def __call__(self, b: B) -> None:
        self.result = list(b.result)


@pytest.mark.flow
class TestGrid:
    def test_flow(self) -> None:
        execution_id = flow()

        execution = flow.execution(unwrap(execution_id))

        assert list(execution.layer(A).foo) == [1, 2, 3]
        assert list(execution.layer(A).bar) == ["a", "b"]
        assert list(execution.layer(B).result) == [("a", 1), ("b", 1), ("a", 2), ("b", 2), ("a", 3), ("b", 3)]
        assert execution.layer(C).result == [("a", 1), ("b", 1), ("a", 2), ("b", 2), ("a", 3), ("b", 3)]


flow2 = Flow(name="Test", datastore=datastores.Memory(), executor=executors.Thread())


@flow2.register()
class A12(Layer):
    foo: List[int]

    def __call__(self) -> None:
        self.shard(foo=[1, 2, 3])


@flow2.register()
class A22(Layer):
    bar: List[str]

    def __call__(self) -> None:
        self.shard(bar=["a", "b"])


@flow2.register(
    foreach=ForEach(parameters=[Parameter(layer=A12, attribute="foo"), Parameter(layer=A22, attribute="bar")])
)
class B2(Layer):
    result: List[Tuple[str, int]]

    def __call__(self, a12: A12, a22: A22) -> None:
        self.result = (a22.bar, a12.foo)  # type: ignore


@flow2.register()
class C2(Layer):
    def __call__(self, b: B2) -> None:
        self.result = list(b.result)


@pytest.mark.flow
class TestTwoGrid:
    def test_flow(eslf) -> None:
        execution_id = flow2()

        execution = flow2.execution(unwrap(execution_id))

        assert list(execution.layer(A12).foo) == [1, 2, 3]
        assert list(execution.layer(A22).bar) == ["a", "b"]
        assert list(execution.layer(B2).result) == [("a", 1), ("b", 1), ("a", 2), ("b", 2), ("a", 3), ("b", 3)]
        assert execution.layer(C2).result == [("a", 1), ("b", 1), ("a", 2), ("b", 2), ("a", 3), ("b", 3)]
