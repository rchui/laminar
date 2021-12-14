"""Configurations for laminar hooks."""

from contextlib import ExitStack, contextmanager
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Generator, Tuple, TypeVar

from laminar.types import annotations

if TYPE_CHECKING:
    from laminar import Layer
else:
    Layer = "Layer"

T = TypeVar("T", bound=Any)

ATTRIBUTE = "annotation"


class annotation(str, Enum):
    execution = "hook::execution"
    retry = "hook::retry"
    schedule = "hook::schedule"

    @staticmethod
    def annotate(hook: T, annotation: "annotation") -> T:
        setattr(hook, ATTRIBUTE, annotation)
        return hook


def execution(hook: T) -> T:
    """Configure an execution hook.

    Usage::

        from laminar.configurations import hooks

        @hooks.execution
        def configure() -> Generator[None, None, None]:
            ...
    """

    return annotation.annotate(hook, annotation.execution)


def retry(hook: T) -> T:
    """Configure a retry hook.

    Usage::

        from laminar.configurations import hooks

        @hooks.retry
        def configure() -> Generator[None, None, None]:
            ...
    """

    return annotation.annotate(hook, annotation.retry)


def schedule(hook: T) -> T:
    """Configure a schedule hook.

    Usage::

        from laminar.configurations import hooks

        @hooks.schedule
        def configure() -> Generator[None, None, None]:
            ...
    """

    return annotation.annotate(hook, annotation.schedule)


def dependencies(*, layer: Layer, hook: Callable[..., Generator[None, None, None]]) -> Tuple[Layer, ...]:
    """Get the dependencies for a hook."""

    return tuple(layer.flow.layer(annotation) for annotation in annotations(hook))


def context(*, layer: Layer, annotation: annotation) -> ExitStack:
    """Get a context manager for all hooks of the annotated type.

    Args:
        layer: Layer the hooks are for.
        annotation: Annotation to get hooks for.

    Returns:
        A context manager with all annotated hooks activated.
    """

    stack = ExitStack()
    for hook in list(vars(type(layer.flow)).values()) + list(vars(type(layer)).values()):
        if getattr(hook, ATTRIBUTE, None) == annotation:
            # Gather any layer dependencies the hook may have
            parameters = dependencies(layer=layer, hook=hook)

            # Create a context for each hook and register it with the exit stack
            hook_context = contextmanager(hook)
            stack.enter_context(hook_context(layer, *parameters))

    return stack
