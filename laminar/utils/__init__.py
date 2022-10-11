"""Shared laminar utilities."""


def stringify(obj: object, name: str, *attrs: str, empty: bool = False) -> str:
    """Create a string representation of an object.

    Args:
        obj: Object the representation is for.
        name: Name of the object
        *attrs: Attributes to include in the representation.
        empty: If the body of the representation should be empty.

    Returns:
        Object's string representation.
    """

    default = {} if empty else vars(obj)
    attrs = tuple(sorted(attrs or default))
    variables = {attr: getattr(obj, attr, None) for attr in sorted(attrs)}
    attributes = ", ".join(f"{key}={repr(value)}" for key, value in variables.items())
    return f"{name}({attributes})"
