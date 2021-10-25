import logging
from typing import List

from laminar import Flow, Layer
from laminar.configurations import layers

logging.basicConfig(level=logging.DEBUG)

flow = Flow(name="TestFlow")

configuration = layers.Configuration(container=layers.Container(image="test"))


@flow.layer
class One(Layer, configuration=configuration):
    def __call__(self) -> None:
        self.foo = "bar"
        self.baz = ["a", "b", "c"]


@flow.layer
class Two(Layer, configuration=configuration):
    def __call__(self, one: One) -> None:
        self.bar = one.foo


@flow.layer
class Three(Layer, configuration=configuration):
    baz: List[str]

    def __call__(self, one: One) -> None:
        self.fork(baz=one.baz)


@flow.layer
class Four(
    Layer, configuration=configuration | layers.ForEach(parameters=[layers.Parameter(cls=Three, attribute="baz")])
):
    def __call__(self, two: Two, three: Three) -> None:
        self.end = [two.bar, list(three.baz)]


if __name__ == "__main__":
    flow()
