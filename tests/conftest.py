import pytest

from laminar import Flow, Layer
from laminar.components import Execution
from laminar.configurations import datastores, executors


@pytest.fixture()
def flow() -> Flow:
    class TestFlow(Flow):
        ...

    flow = TestFlow(datastore=datastores.Memory(), executor=executors.Thread())
    flow.execution = Execution(id="test-execution", flow=flow)
    return flow


@pytest.fixture()
def layer(flow: Flow) -> Layer:
    flow.register()(Layer)
    return flow.layer(Layer, index=0, attempt=1, splits=2)
