"""Unit tests for laminar.configurations.hooks"""

from laminar.configurations import hooks


class TestAnnotation:
    def test_annotate(self) -> None:
        def func() -> None:
            ...

        func = hooks.Annotation.annotate(func, hooks.Annotation.execution)
        assert hooks.Annotation.get(func) == hooks.Annotation.execution

    def test_execution(self) -> None:
        def func() -> None:
            ...

        func = hooks.execution(func)
        assert hooks.Annotation.get(func) == hooks.Annotation.execution

    def test_retry(self) -> None:
        def func() -> None:
            ...

        func = hooks.retry(func)
        assert hooks.Annotation.get(func) == hooks.Annotation.retry

    def test_submit(self) -> None:
        def func() -> None:
            ...

        func = hooks.submit(func)
        assert hooks.Annotation.get(func) == hooks.Annotation.submit
