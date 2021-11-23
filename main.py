import logging
from typing import List, Set

from laminar import Flow, Layer
from laminar.configurations import datastores, executors, layers

logging.basicConfig(level=logging.INFO)


flow = Flow(name="TestFlow", datastore=datastores.Local(), executor=executors.Docker())
# flow = Flow(name="TestFlow", datastore=datastores.Memory(), executor=executors.Thread())

container = layers.Container(image="test")


@flow.register(container=container)
class One(Layer):
    baz: List[str]
    foo: str

    def __call__(self) -> None:
        self.foo = "bar"
        self.shard(baz=["a", "b", "c"])

    def __next__(self) -> Set[Layer]:
        return self.next(Two)


@flow.register(container=container)
class Two(Layer):
    def __call__(self, one: One) -> None:  # type: ignore
        self.bar = one.foo
        print(self.bar)


@flow.register(container=container, foreach=layers.ForEach(parameters=[layers.Parameter(layer=One, attribute="baz")]))
class Three(Layer):
    baz: List[str]

    def __call__(self, one: One) -> None:  # type: ignore
        self.baz = one.baz
        print(self.baz)


@flow.register(
    container=container, foreach=layers.ForEach(parameters=[layers.Parameter(layer=Three, attribute="baz", index=None)])
)
class Five(Layer):
    baz: List[str]

    def __call__(self, three: Three) -> None:  # type: ignore
        self.baz = three.baz
        print(self.baz)


@flow.register(container=container)
class Four(Layer):
    def __call__(self, two: Two, five: Five) -> None:  # type: ignore
        self.end = [two.bar, list(five.baz)]
        print(self.end)


if __name__ == "__main__":
    flow()
