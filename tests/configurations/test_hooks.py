"""Unit tests for laminar.configurations.hooks"""

from laminar.configurations import hooks


class TestAnnotation:
    def test_annotate(self) -> None:
        def func() -> None:
            ...

        func = hooks.annotation.annotate(func, hooks.annotation.execution)
        assert getattr(func, hooks.ATTRIBUTE) == hooks.annotation.execution

    def test_execution(self) -> None:
        def func() -> None:
            ...

        func = hooks.execution(func)
        assert getattr(func, hooks.ATTRIBUTE) == hooks.annotation.execution

    def test_retry(self) -> None:
        def func() -> None:
            ...

        func = hooks.retry(func)
        assert getattr(func, hooks.ATTRIBUTE) == hooks.annotation.retry

    def test_schedule(self) -> None:
        def func() -> None:
            ...

        func = hooks.schedule(func)
        assert getattr(func, hooks.ATTRIBUTE) == hooks.annotation.schedule
