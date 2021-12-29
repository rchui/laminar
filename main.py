import logging
from typing import Generator, List

from laminar import Flow, Layer
from laminar.components import Parameters
from laminar.configurations import datastores, executors, hooks, layers
from laminar.types import unwrap

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

container = layers.Container(image="rchui/laminar:test-local")
datastore = datastores.Local()

flow = Flow(name="DockerFlow", datastore=datastore, executor=executors.Docker(concurrency=2))
flow2 = Flow(name="ThreadFlow", datastore=datastore, executor=executors.Thread())


@flow.register(container=container)
@flow2.register()
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


@flow.register(container=container)
@flow2.register()
class Two(Layer):
    def __call__(self, one: One, three: "Three") -> None:
        self.bar = one.foo
        print(self.bar)


three_foreach = layers.ForEach(parameters=[layers.Parameter(layer=One, attribute="baz")])


@flow.register(container=container, foreach=three_foreach)
@flow2.register(foreach=three_foreach)
class Three(Layer):
    baz: List[str]

    def __call__(self, one: One) -> None:
        self.baz = one.baz
        print(self.baz)

    @hooks.submit
    def configure_container(self, one: One) -> Generator[None, None, None]:
        self.configuration.container.memory = {"a": 1000, "b": 15000, "c": 2000}[one.baz[unwrap(self.index)]]
        yield


five_foreach = layers.ForEach(parameters=[layers.Parameter(layer=Three, attribute="baz", index=None)])


@flow.register(container=container, foreach=five_foreach)
@flow2.register(foreach=five_foreach)
class Five(Layer):
    baz: List[str]

    def __call__(self, three: Three) -> None:
        self.baz = three.baz
        print(self.baz)


@flow.register(container=container)
@flow2.register()
class Four(Layer):
    def __call__(self, two: Two, five: Five) -> None:
        self.end = [two.bar, list(five.baz)]
        print(self.end)


if __name__ == "__main__":
    execution = None

    if not flow.execution:
        execution = flow.parameters(foo="bar")
    flow(execution=execution)

    if not flow2.execution:
        execution = flow2.parameters(foo="bar")
    flow2(execution=execution)
