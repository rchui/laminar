"""Shared laminar types."""

from typing import TYPE_CHECKING, Any, Callable, Optional, Tuple, TypeVar, get_type_hints

if TYPE_CHECKING:
    from laminar import Execution, Layer

T = TypeVar("T")


def hints(execution: "Execution", function: Callable[..., Any]) -> Tuple["Layer", ...]:
    """Get the type hints for a given function.

    Args:
        execution: Execution to get layers for.
        function (Callable[..., Any]): Function to get type hints for.

    Returns:
        Ordered type hints.
    """

    return tuple(
        execution.layer(hint)
        for hint in (annotation for parameter, annotation in get_type_hints(function).items() if parameter != "return")
    )


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
