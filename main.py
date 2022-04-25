import logging
from typing import Generator, List

from laminar import Flow, Layer
from laminar.components import Parameters
from laminar.configurations import executors, hooks, layers
from laminar.types import unwrap

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

container = layers.Container(image="rchui/laminar:test-local")


class TestFlow(Flow):
    ...


@TestFlow.register(container=container)
class One(Layer):
    baz: List[str]
    foo: str

    def __call__(self, parameters: Parameters) -> None:
        self.foo = parameters.foo
        self.shard(baz=["a", "b", "c"])

    @hooks.execution
    def configure_hello(self) -> Generator[None, None, None]:
        logger.info("hello before")
        yield
        logger.info("hello after")


@TestFlow.register(container=container)
class Two(Layer):
    def __call__(self, one: One, three: "Three") -> None:
        self.bar = one.foo
        print(self.bar)


@TestFlow.register(
    container=container, foreach=layers.ForEach(parameters=[layers.Parameter(layer=One, attribute="baz")])
)
class Three(Layer):
    baz: List[str]

    def __call__(self, one: One) -> None:
        self.baz = one.baz
        print(self.baz)

    @hooks.submission
    def configure_container(self, one: One) -> None:
        self.configuration.container.memory = {"a": 1000, "b": 15000, "c": 2000}[one.baz[unwrap(self.index)]]


@TestFlow.register(
    container=container, foreach=layers.ForEach(parameters=[layers.Parameter(layer=Three, attribute="baz", index=None)])
)
class Five(Layer):
    baz: List[str]

    def __call__(self, three: Three) -> None:
        self.baz = three.baz
        print(self.baz)


@TestFlow.register(container=container)
class Four(Layer):
    def __call__(self, two: Two, five: Five) -> None:
        self.end = [two.bar, list(five.baz)]
        print(self.end)


class DockerFlow(TestFlow):
    ...


class ThreadFlow(TestFlow):
    ...


if __name__ == "__main__":
    flow: Flow = DockerFlow()
    flow() if flow.execution.running else flow(foo="bar")

    flow = ThreadFlow(executor=executors.Thread())
    flow() if flow.execution.running else flow(foo="bar")
