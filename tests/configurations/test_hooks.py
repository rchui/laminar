"""Unit tests for laminar.configurations.hooks"""

from typing import Generator

from laminar.configurations import hooks


class TestAnnotation:
    def test_annotate(self) -> None:
        def func() -> Generator[None, None, None]:
            ...

        func = hooks.annotation.annotate(func, hooks.annotation.execution)
        assert hooks.annotation.get(func) == hooks.annotation.execution

    def test_execution(self) -> None:
        def func() -> Generator[None, None, None]:
            ...

        func = hooks.execution(func)
        assert hooks.annotation.get(func) == hooks.annotation.execution

    def test_retry(self) -> None:
        def func() -> Generator[None, None, None]:
            ...

        func = hooks.retry(func)
        assert hooks.annotation.get(func) == hooks.annotation.retry

    def test_submission(self) -> None:
        def func() -> Generator[None, None, None]:
            ...

        func = hooks.submission(func)
        assert hooks.annotation.get(func) == hooks.annotation.submission
