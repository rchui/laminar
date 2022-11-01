import inspect
from contextlib import ExitStack, contextmanager
from typing import TYPE_CHECKING, TypeVar

from laminar.configurations.hooks import annotation
from laminar.types import hints

if TYPE_CHECKING:
    from laminar import Layer

T = TypeVar("T")


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


def submission(hook: T) -> T:
    """Configure a submission hook.

    Usage::

        from laminar.configurations import hooks

        @hooks.submission
        def configure() -> Generator[None, None, None]:
            ...
    """

    return annotation.annotate(hook, annotation.submission)


def context(*, layer: "Layer", annotation: str) -> ExitStack:
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
        parameters = hints(layer.execution, hook)

        # Create a context manager for the generator and register it with the exit stack
        if inspect.isgeneratorfunction(hook):
            manager = contextmanager(hook)
            stack.enter_context(manager(layer, *parameters))

        # Call the hook function
        else:
            hook(layer, *parameters)

    return stack
