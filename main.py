import logging
from typing import List

from laminar import Flow, Layer
from laminar.configurations import layers

logging.basicConfig(level=logging.INFO)

flow = Flow(name="TestFlow")

configuration = layers.Configuration(container=layers.Container(image="test"))


@flow.layer
class One(Layer, configuration=configuration):
    baz: str

    def __call__(self) -> None:
        self.foo = "bar"
        self.shard(baz=["a", "b", "c"])


@flow.layer
class Two(Layer, configuration=configuration):
    def __call__(self, one: One) -> None:
        self.bar = one.foo


@flow.layer
class Three(
    Layer, configuration=configuration | layers.ForEach(parameters=[layers.Parameter(layer=One, attribute="baz")])
):
    baz: List[str]

    def __call__(self, one: One) -> None:
        self.baz = one.baz
        print(self.baz)


@flow.layer
class Five(
    Layer,
    configuration=configuration
    | layers.ForEach(parameters=[layers.Parameter(layer=Three, attribute="baz", index=None)]),
):
    baz: List[str]

    def __call__(self, three: Three) -> None:
        self.baz = three.baz
        print(self.baz)


@flow.layer
class Four(Layer, configuration=configuration):
    def __call__(self, two: Two, five: Five) -> None:
        self.end = [two.bar, list(five.baz)]
        print(self.end)


if __name__ == "__main__":
    flow()
