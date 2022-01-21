"""Configurations for laminar hooks."""

import inspect
from contextlib import ExitStack, contextmanager
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Generator, Optional, TypeVar

from laminar.types import annotations

if TYPE_CHECKING:
    from laminar import Layer
else:
    Layer = "Layer"

T = TypeVar("T", bound=Any)

ATTRIBUTE = "annotation"


class Annotation(str, Enum):
    execution = "hook::execution"
    retry = "hook::retry"
    submission = "hook::submission"

    @staticmethod
    def annotate(hook: T, annotation: "Annotation") -> T:
        setattr(hook, ATTRIBUTE, annotation)
        return hook

    @staticmethod
    def get(hook: Callable[..., Generator[Any, None, None]]) -> Optional[str]:
        return getattr(hook, ATTRIBUTE, None)


def execution(hook: T) -> T:
    """Configure an execution hook.

    Usage::

        from laminar.configurations import hooks

        @hooks.execution
        def configure() -> Generator[None, None, None]:
            ...
    """

    return Annotation.annotate(hook, Annotation.execution)


def retry(hook: T) -> T:
    """Configure a retry hook.

    Usage::

        from laminar.configurations import hooks

        @hooks.retry
        def configure() -> Generator[None, None, None]:
            ...
    """

    return Annotation.annotate(hook, Annotation.retry)


def submission(hook: T) -> T:
    """Configure a submission hook.

    Usage::

        from laminar.configurations import hooks

        @hooks.submission
        def configure() -> Generator[None, None, None]:
            ...
    """

    return Annotation.annotate(hook, Annotation.submission)


def context(*, layer: Layer, annotation: Annotation) -> ExitStack:
    """Get a context manager and results for all hooks of the annotated type.

    Args:
        layer: Layer the hooks are for.
        annotation: Annotation to get hooks for.

    Returns:
        A context manager with all annotated hooks activated.
    """

    stack = ExitStack()
    for hook in layer.hooks.get(annotation, []):
        # Gather any layer dependencies the hook may have
        parameters = annotations(layer.flow, hook)

        # Create a context manager for the generator and register it with the exit stack
        if inspect.isgeneratorfunction(hook):
            manager = contextmanager(hook)
            stack.enter_context(manager(layer, *parameters))

        # Call the hook function
        else:
            hook(layer, *parameters)

    return stack
