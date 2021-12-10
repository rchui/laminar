from typing import Optional, TypeVar

T = TypeVar("T")


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
