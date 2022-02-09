"""Shared laminar types."""

from typing import TYPE_CHECKING, Any, Callable, Optional, Tuple, Type, TypeVar, get_type_hints

if TYPE_CHECKING:
    from laminar import Flow, Layer
else:
    Flow = "Flow"
    Layer = "Layer"

T = TypeVar("T")
LayerType = TypeVar("LayerType", bound=Type[Layer])


def hints(function: Callable[..., Any]) -> Tuple[Any, ...]:
    """Get the type hints for a given function.

    Args:
        function (Callable[..., Any]): Function to get annotations for.

    Returns:
        Tuple[Any, ...]: Ordered type annotations.
    """

    return tuple(annotation for parameter, annotation in get_type_hints(function).items() if parameter != "return")


def annotations(flow: Flow, func: Callable[..., Any]) -> Tuple[Layer, ...]:
    """Get the layer annotations for a given function.

    Args:
        flow: Flow to get layers for.
        func: Function to get layer annotations for.

    Returns:
        Type[Layer, ...]: Ordered layer type annotations.
    """

    return tuple(flow.layer(annotation) for annotation in hints(func))


def unwrap(option: Optional[T], default: Optional[T] = None) -> T:
    """Unwrap an optional value.

    Usage::

        unwrap("a")
        >>> "a"
        unwrap(None, "a")
        >>> "a"
        unwrap(None)
        >>> ValueError

    Args:
        option: Optional value to unwrap.
        default: Default value if the optional value is None.

    Raises:
        ValueError: If the option is None and no default is set.

    Returns:
        Unwrapped optional value.
    """

    if option is None:
        if default is None:
            raise ValueError("Value is None when it shouldn't be.")
        return unwrap(default)
    return option
