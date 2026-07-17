from collections.abc import Callable, Generator
from typing import Any, TypeVar

T = TypeVar("T")

ATTRIBUTE = "annotation"

entry = "hook::entry"
execution = "hook::execution"
retry = "hook::retry"
submission = "hook::submission"


def annotate(hook: T, annotation: str) -> T:
    setattr(hook, ATTRIBUTE, annotation)
    return hook


def get(hook: Callable[..., Generator[Any, None, None]]) -> str | None:
    return getattr(hook, ATTRIBUTE, None)
