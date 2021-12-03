from typing import Optional, TypeVar

T = TypeVar("T")


def unwrap(wrapped: Optional[T]) -> T:
    if wrapped is None:
        raise ValueError("Value is None when it shouldn't be.")
    return wrapped
