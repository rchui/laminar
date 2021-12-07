"""Test foreach flows."""

from typing import List

from laminar import Flow, Layer
from laminar.configurations import datastores, executors
from laminar.configurations.layers import ForEach, Parameter
from laminar.utils import unwrap

flow = Flow(name="Test", datastore=datastores.Memory(), executor=executors.Thread())


@flow.register()
class A(Layer):
    def __call__(self) -> None:
        self.shard(foo=[1, 2, 3])


@flow.register(foreach=ForEach(parameters=[Parameter(layer=A, attribute="foo")]))
class B(Layer):
    foo: List[int]

    def __call__(self, a: A) -> None:
        self.foo = a.foo + unwrap(self.index) ** 2


@flow.register()
class C(Layer):
    def __call__(self, b: B) -> None:
        self.foo = [value + i for i, value in enumerate(b.foo)]


class TestForEach:
    def test_flow(self) -> None:
        execution = flow()

        results = flow.results(unwrap(execution))

        assert list(results.layer(A).foo) == [1, 2, 3]
        assert list(results.layer(B).foo) == [1, 3, 7]
        assert results.layer(C).foo == [1, 4, 9]
