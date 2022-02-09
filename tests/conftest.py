import pytest

from laminar import Flow, Layer
from laminar.components import Execution
from laminar.configurations.datastores import Memory
from laminar.configurations.executors import Thread


@pytest.fixture()
def flow() -> Flow:
    flow = Flow(name="TestFlow", datastore=Memory(), executor=Thread())
    flow.execution = Execution(id="test-execution", flow=flow)
    return flow


@pytest.fixture()
def layer(flow: Flow) -> Layer:
    flow.register()(Layer)
    return flow.layer(Layer, index=0, attempt=1, splits=2)
