"""Test conditional branching."""

import pytest

from laminar import Flow, Layer
from laminar.configurations import datastores, executors, hooks


class ConditionalFlow(Flow):
    ...


@ConditionalFlow.register
class A(Layer):
    def __call__(self) -> None:
        self.foo = "bar"


# Always skip B
@ConditionalFlow.register
class B(Layer):
    def __call__(self, a: A) -> None:
        self.foo = a.foo

    @hooks.entry
    def failure(self) -> bool:
        return False


# C executes because A executed
@ConditionalFlow.register
class C(Layer):
    def __call__(self, a: A) -> None:
        self.foo = "baz"


# D skips because B was skipped
@ConditionalFlow.register
class D(Layer):
    def __call__(self, b: B) -> None:
        self.foo = b.foo


# Force E to execute even though D skipped
@ConditionalFlow.register
class E(Layer):
    def __call__(self, c: C, d: D) -> None:
        if d.state.finished:
            self.foo = [c.foo, d.foo]
        else:
            self.foo = [c.foo]

    @hooks.entry
    def success(self) -> bool:
        return True


@pytest.mark.flow
def test_flow() -> None:
    flow = ConditionalFlow(datastore=datastores.Memory(), executor=executors.Thread())
    execution = flow()

    assert execution.layer(A).state.finished is True
    assert execution.layer(A).foo == "bar"
    assert execution.layer(B).state.finished is False
    assert execution.layer(C).state.finished is True
    assert execution.layer(C).foo == "baz"
    assert execution.layer(D).state.finished is False
    assert execution.layer(E).state.finished is True
    assert execution.layer(E).foo == ["baz"]
