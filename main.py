import logging
from typing import List

from laminar import Flow, Layer
from laminar.configurations import layers

logging.basicConfig(level=logging.INFO)

flow = Flow(name="TestFlow")

container = layers.Container(image="test")


@flow.layer(container=container)
class One(Layer):
    baz: str

    def __call__(self) -> None:
        self.foo = "bar"
        self.shard(baz=["a", "b", "c"])


@flow.layer(container=container)
class Two(Layer):
    def __call__(self, one: One) -> None:
        self.bar = one.foo


@flow.layer(container=container, foreach=layers.ForEach(parameters=[layers.Parameter(layer=One, attribute="baz")]))
class Three(Layer):
    baz: List[str]

    def __call__(self, one: One) -> None:
        self.baz = one.baz
        print(self.baz)


@flow.layer(
    container=container, foreach=layers.ForEach(parameters=[layers.Parameter(layer=Three, attribute="baz", index=None)])
)
class Five(Layer):
    baz: List[str]

    def __call__(self, three: Three) -> None:
        self.baz = three.baz
        print(self.baz)


@flow.layer(container=container)
class Four(Layer):
    def __call__(self, two: Two, five: Five) -> None:
        self.end = [two.bar, list(five.baz)]
        print(self.end)


if __name__ == "__main__":
    flow()
