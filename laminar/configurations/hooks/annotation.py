from typing import Any, Callable, Generator, Optional, TypeVar

T = TypeVar("T")

ATTRIBUTE = "annotation"

entry = "hook::entry"
execution = "hook::execution"
retry = "hook::retry"
submission = "hook::submission"


def annotate(hook: T, annotation: str) -> T:
    setattr(hook, ATTRIBUTE, annotation)
    return hook


def get(hook: Callable[..., Generator[Any, None, None]]) -> Optional[str]:
    return getattr(hook, ATTRIBUTE, None)
