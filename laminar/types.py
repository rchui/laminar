import inspect
from typing import TYPE_CHECKING, Any, Callable, Tuple, Type, TypeVar

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

    return tuple(parameter.annotation for parameter in inspect.signature(function).parameters.values())
