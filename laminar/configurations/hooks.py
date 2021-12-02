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
    schedule = "hook::schedule"

    @staticmethod
    def annotate(hook: T, annotation: "annotation") -> T:
        setattr(hook, ATTRIBUTE, annotation)
        return hook


def execution(hook: T) -> T:
    return annotation.annotate(hook, annotation.execution)


def schedule(hook: T) -> T:
    return annotation.annotate(hook, annotation.schedule)


def dependencies(*, layer: Layer, hook: Callable[..., Generator[None, None, None]]) -> Tuple[Layer, ...]:
    return tuple(layer.flow.layer(annotation) for annotation in annotations(hook))


def context(*, layer: Layer, annotation: annotation) -> ExitStack:
    stack = ExitStack()
    for hook in list(vars(type(layer.flow)).values()) + list(vars(type(layer)).values()):
        if getattr(hook, ATTRIBUTE, None) == annotation:
            # Gather any layer dependencies the hook may have
            parameters = dependencies(layer=layer, hook=hook)

            # Create a context for each hook and register it with the exit stack
            hook_context = contextmanager(hook)
            stack.enter_context(hook_context(layer, *parameters))

    return stack
