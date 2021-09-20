import logging

from laminar import Flow, Layer
from laminar.layers import Container, Dependencies, Resources

logging.basicConfig(level=logging.INFO)

flow = Flow(name="hello world")


@flow.layer(container=Container(image="python:3.7"))
class One(Layer):
    foo: str = "bar"


@flow.layer(dependencies=Dependencies(bar=One), resources=Resources(memory=3500))
class Two(Layer):
    foo: str = "baz"


if __name__ == "__main__":
    print(flow.__repr__())
    print(flow.dag)

    flow()
