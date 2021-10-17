import logging

from laminar import Flow, Layer
from laminar.layers import Container, Dependencies

logging.basicConfig(level=logging.INFO)


class HelloWorld(Flow):
    ...


flow = HelloWorld()


class TestFlow(Flow):
    ...


flow2 = TestFlow()


class HelloContainer(Container):
    image: str = "test"


@flow.layer
@flow2.layer
class One(Layer, container=HelloContainer()):
    foo: str = "bar"


@flow.layer
class Two(Layer, container=HelloContainer(), dependencies=Dependencies(foo=One)):
    foo: str


@flow.layer
class Three(Layer, container=HelloContainer(), dependencies=Dependencies(foo=One)):
    foo: str


@flow.layer
class Four(Layer, container=HelloContainer(), dependencies=Dependencies(foo=Three)):
    foo: str


@flow.layer
class Five(Layer, container=HelloContainer(), dependencies=Dependencies(One)):
    bar: bool = False


if __name__ == "__main__":
    # print(flow.__repr__())
    # print(flow.dag)

    flow()
    flow2()
