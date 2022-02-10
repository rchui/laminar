"""Shared laminar utilities."""


def stringify(obj: object, name: str, *attrs: str) -> str:
    """Create a string representation of an object.

    Args:
        obj: Object the representation is for.
        name: Name of the object
        *attrs: Attributes to include in the representation.

    Returns:
        Object's string representation.
    """

    variables = {attr: getattr(obj, attr, None) for attr in attrs} if attrs else vars(obj)
    attributes = ", ".join(f"{key}={repr(value)}" for key, value in variables.items())
    return f"{name}({attributes})"
