"""Test resuming flows."""

import pytest

from laminar import Flow, Layer
from laminar.configurations import datastores, executors


class ResumeFlow(Flow): ...


@ResumeFlow.register
class A(Layer):
    def __call__(self) -> None: ...


@ResumeFlow.register
class B(Layer):
    fail: bool = True

    def __call__(self, a: A) -> None:
        if self.fail:
            raise RuntimeError


@ResumeFlow.register
class C(Layer):
    def __call__(self, b: B) -> None: ...


@pytest.mark.flow
def test_flow() -> None:
    flow = ResumeFlow(datastore=datastores.Memory(), executor=executors.Thread())
    execution_id = "test-execution"

    # Catch failure
    try:
        flow(execution=execution_id)
    except RuntimeError: ...

    execution = flow.execution(execution_id)

    assert execution.layer(A).state.finished is True
    assert execution.layer(B).state.finished is False
    assert execution.layer(C).state.finished is False

    # Retry failed execution
    B.fail = False
    execution.resume()

    assert execution.layer(A).state.finished is True
    assert execution.layer(B).state.finished is True
    assert execution.layer(C).state.finished is True
