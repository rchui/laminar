"""Shared laminar types."""

from typing import TYPE_CHECKING, Any, Callable, Optional, Tuple, Type, TypeVar, get_type_hints

if TYPE_CHECKING:
    from laminar import Layer
else:
    Layer = "Layer"

T = TypeVar("T")
LayerType = TypeVar("LayerType", bound=Type[Layer])


def annotations(function: Callable[..., Any]) -> Tuple[Any, ...]:
    """Get the type annotations for a given function.

    Args:
        function (Callable[..., Any]): Function to get annotations for.

    Returns:
        Tuple[Any, ...]: Ordered type annotations.
    """

    return tuple(annotation for parameter, annotation in get_type_hints(function).items() if parameter != "return")


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
