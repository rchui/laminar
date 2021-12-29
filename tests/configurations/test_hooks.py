"""Unit tests for laminar.configurations.hooks"""

from typing import Generator

from laminar.configurations import hooks


class TestAnnotation:
    def test_annotate(self) -> None:
        def func() -> Generator[None, None, None]:
            ...

        func = hooks.Annotation.annotate(func, hooks.Annotation.execution)
        assert hooks.Annotation.get(func) == hooks.Annotation.execution

    def test_execution(self) -> None:
        def func() -> Generator[None, None, None]:
            ...

        func = hooks.execution(func)
        assert hooks.Annotation.get(func) == hooks.Annotation.execution

    def test_retry(self) -> None:
        def func() -> Generator[None, None, None]:
            ...

        func = hooks.retry(func)
        assert hooks.Annotation.get(func) == hooks.Annotation.retry

    def test_submission(self) -> None:
        def func() -> Generator[None, None, None]:
            ...

        func = hooks.submission(func)
        assert hooks.Annotation.get(func) == hooks.Annotation.submission
