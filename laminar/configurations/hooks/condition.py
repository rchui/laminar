from typing import TYPE_CHECKING, Any, List, TypeVar

from laminar.configurations.hooks import annotation

if TYPE_CHECKING:
    from laminar import Layer

T = TypeVar("T")


def entry(hook: T) -> T:
    """Configure an entry hook

    Usage::

        from laminar.configurations import entry

        @hooks.entry
        def enter() -> bool:
            ...
    """

    return annotation.annotate(hook, annotation.entry)


def gather(*, layer: "Layer", annotation: str) -> List[Any]:
    """Get values returned by all hooks of the annotated type.

    Args:
        layer: Layer the hooks are for.
        annotation: Annotation to get the hooks for.

    Returns:
        Return values for each hook.
    """

    return [hook(layer, *layer._parameters[hook.__name__]) for hook in layer.hooks.get(annotation, [])]
