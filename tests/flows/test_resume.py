"""Test resuming flows."""

import pytest

from laminar import Flow, Layer
from laminar.configurations import datastores, executors

flow = Flow(name="Test", datastore=datastores.Memory(), executor=executors.Thread())


@flow.register()
class A(Layer):
    def __call__(self) -> None:
        ...


@flow.register()
class B(Layer):
    fail: bool = True

    def __call__(self, a: A) -> None:
        if self.fail:
            raise RuntimeError


@flow.register()
class C(Layer):
    def __call__(self, b: B) -> None:
        ...


@pytest.mark.flow
class TestResume:
    def test_flow(self) -> None:
        execution_id = "test-execution"

        # Catch failure
        try:
            flow(execution=execution_id)
        except RuntimeError:
            ...

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
