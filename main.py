import logging

from laminar import Flow, Layer
from laminar.layers import Container, Dependencies

logging.basicConfig(level=logging.INFO)


class HelloWorld(Flow):
    ...


flow = HelloWorld()
container = Container(image="test")


@flow.layer(container=container)
class One(Layer):
    foo: str = "bar"


@flow.layer(container=container, dependencies=Dependencies(foo=One))
class Two(Layer):
    foo: str


@flow.layer(container=container, dependencies=Dependencies(foo=One))
class Three(Layer):
    foo: str


@flow.layer(container=container, dependencies=Dependencies(foo=Three))
class Four(Layer):
    foo: str


@flow.layer(container=container, dependencies=Dependencies(One))
class Five(Layer):
    bar: bool = False


if __name__ == "__main__":
    print(flow.__repr__())
    print(flow.dag)

    flow()
