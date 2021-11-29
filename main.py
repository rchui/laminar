import logging
from typing import Generator, List

from laminar import Flow, Layer
from laminar.configurations import datastores, executors, hooks, layers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

flow = Flow(name="Dockerflow", datastore=datastores.Local(), executor=executors.Docker())
flow2 = Flow(name="ThreadFlow", datastore=datastores.Local(), executor=executors.Thread())

container = layers.Container(image="test")


@flow.register(container=container)
@flow2.register()
class One(Layer):
    baz: List[str]
    foo: str

    def __call__(self) -> None:
        self.foo = "bar"
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

    @hooks.schedule
    def configure_container(self, one: One) -> Generator[None, None, None]:
        assert self.index is not None
        self.configuration.container.memory = {"a": 1000, "b": 15000, "c": 2000}[one.baz[self.index]]
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
    flow()
    flow2()
