"""Test foreach flows."""

from typing import List, Tuple

import pytest

from laminar import Flow, Layer
from laminar.configurations import datastores, executors
from laminar.configurations.layers import ForEach, Parameter
from laminar.utils import unwrap

flow = Flow(name="Test", datastore=datastores.Memory(), executor=executors.Thread())


@flow.register()
class A(Layer):
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
        execution = flow()

        results = flow.results(unwrap(execution))

        assert list(results.layer(A).foo) == [1, 2, 3]
        assert list(results.layer(A).bar) == ["a", "b"]
        assert list(results.layer(B).result) == [("a", 1), ("b", 1), ("a", 2), ("b", 2), ("a", 3), ("b", 3)]
        assert results.layer(C).result == [("a", 1), ("b", 1), ("a", 2), ("b", 2), ("a", 3), ("b", 3)]


flow2 = Flow(name="Test", datastore=datastores.Memory(), executor=executors.Thread())


@flow2.register()
class A12(Layer):
    def __call__(self) -> None:
        self.shard(foo=[1, 2, 3])


@flow2.register()
class A22(Layer):
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
        execution = flow2()

        results = flow2.results(unwrap(execution))

        assert list(results.layer(A12).foo) == [1, 2, 3]
        assert list(results.layer(A22).bar) == ["a", "b"]
        assert list(results.layer(B2).result) == [("a", 1), ("b", 1), ("a", 2), ("b", 2), ("a", 3), ("b", 3)]
        assert results.layer(C2).result == [("a", 1), ("b", 1), ("a", 2), ("b", 2), ("a", 3), ("b", 3)]
