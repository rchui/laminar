"""Test conditional branching."""

import pytest

from laminar import Flow, Layer
from laminar.configurations import datastores, executors
from laminar.types import unwrap

flow = Flow(name="Test", datastore=datastores.Memory(), executor=executors.Thread())


@flow.register()
class A(Layer):
    def __call__(self) -> None:
        self.foo = "bar"


# Always skip B
@flow.register()
class B(Layer):
    def __call__(self, a: A) -> None:
        self.foo = a.foo

    def __enter__(self) -> bool:
        return False


# C executes because A executed
@flow.register()
class C(Layer):
    def __call__(self, a: A) -> None:
        self.foo = "baz"


# D skips because B was skipped
@flow.register()
class D(Layer):
    def __call__(self, b: B) -> None:
        self.foo = b.foo


# Force E to execute even though D skipped
@flow.register()
class E(Layer):
    def __call__(self, c: C, d: D) -> None:
        if d.state.finished:
            self.foo = [c.foo, d.foo]
        else:
            self.foo = [c.foo]

    def __enter__(self) -> bool:
        return True


@pytest.mark.flow
class TestConditionalBranching:
    def test_flow(self) -> None:
        execution_id = flow()

        execution = flow.execution(unwrap(execution_id))

        assert execution.layer(A).state.finished is True
        assert execution.layer(A).foo == "bar"
        assert execution.layer(B).state.finished is False
        assert execution.layer(C).state.finished is True
        assert execution.layer(C).foo == "baz"
        assert execution.layer(D).state.finished is False
        assert execution.layer(E).state.finished is True
        assert execution.layer(E).foo == ["baz"]
