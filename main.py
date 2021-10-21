import logging
from typing import List

from laminar import Flow, Layer
from laminar.configurations.layers import Container

logging.basicConfig(level=logging.INFO)

flow = Flow(name="TestFlow")

container = Container(image="test")


@flow.layer
class One(Layer, container=container):
    def __call__(self) -> None:
        self.foo = "bar"
        self.baz = ["a", "b", "c"]


@flow.layer
class Two(Layer, container=container):
    def __call__(self, one: One) -> None:
        self.bar = one.foo


@flow.layer
class Three(Layer, container=container):
    baz: List[str]

    def __call__(self, one: One) -> None:
        self.fork(baz=one.baz)


@flow.layer
class Four(Layer, container=container):
    def __call__(self, two: Two, three: Three) -> None:
        self.end = [two.bar, three.baz]


if __name__ == "__main__":
    flow()
