from typing import TYPE_CHECKING, Any, Callable, Tuple, Type, TypeVar, get_type_hints

if TYPE_CHECKING:
    from laminar import Layer
else:
    Layer = "Layer"

LayerType = TypeVar("LayerType", bound=Type[Layer])


def annotations(function: Callable[..., Any]) -> Tuple[Any, ...]:
    """Get the type annotations for a given function.

    Args:
        function (Callable[..., Any]): Function to get annotations for.

    Returns:
        Tuple[Any, ...]: Ordered type annotations.
    """

    return tuple(annotation for parameter, annotation in get_type_hints(function).items() if parameter != "return")
