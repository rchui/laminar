import asyncio
import contextlib
import os
from typing import Any, Dict, TypeVar, cast


class Attributes(contextlib.ContextDecorator):
    def __init__(self, cls: object, **attributes: Any) -> None:
        """Modify a class's attributes.

        Args:
            cls (object): Class to modify
            **attributes (Any): Attribute key/value pairs to modify.
        """

        self.cls = cls
        self.attributes = attributes
        self._attributes: Dict[str, Any] = {}

    def __enter__(self) -> "Attributes":
        """Modify the class attributes."""

        for key, value in self.attributes.items():
            if hasattr(self.cls, key):
                self._attributes[key] = getattr(self.cls, key, None)
            setattr(self.cls, key, value)

        return self

    def __exit__(self, *_: Any) -> None:
        """Revert the class attribute changes."""

        for key in self.attributes:
            if key in self._attributes:
                setattr(self.cls, key, self._attributes[key])
            else:
                delattr(self.cls, key)


class Environment(contextlib.ContextDecorator):
    def __init__(self, **variables: Any) -> None:
        self.variables = {key: str(value) for key, value in variables.items()}

    def __enter__(self) -> "Environment":
        """Modify environment"""

        self.old = dict(os.environ)
        os.environ.update(self.variables)
        return self

    def __exit__(self, *_: Any) -> None:
        """Revert environment changes"""

        os.environ.clear()
        os.environ.update(self.old)


T = TypeVar("T", bound=Any)


def EventLoop(func: T) -> T:
    """Execute the decorated function in an asyncio event loop.

    Usage::

        from laminar.utils import contexts

        @contexts.EventLoop
        async def main() -> None:
            ...
    """

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        asyncio.run(func(*args, **kwargs))

    return cast("T", wrapper)
