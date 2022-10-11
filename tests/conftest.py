import pytest

from laminar import Flow, Layer
from laminar.configurations import datastores, executors


@pytest.fixture()
def flow() -> Flow:
    class TestFlow(Flow):
        ...

    flow = TestFlow(datastore=datastores.Memory(), executor=executors.Thread())
    flow.execution("test-execution")
    return flow


@pytest.fixture()
def layer(flow: Flow) -> Layer:
    flow.register()(Layer)
    return flow.execution.layer(Layer, index=0, attempt=1, splits=2)
