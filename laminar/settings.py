"""Laminar flow configurations."""

import sys
from typing import Any, Type, TypeVar, cast

from pydantic import BaseSettings

T = TypeVar("T")


def setting(category: Type[T]) -> T:
    def setting_getter(self: Any, key: str = category.__name__.lower()) -> T:
        setattr(self, f"_{key}", getattr(self, f"_{key}", None) or category())  # type: ignore
        return getattr(self, f"_{key}")

    return cast(T, property(setting_getter))


class Python:
    major, minor, micro = sys.version_info.major, sys.version_info.minor, sys.version_info.micro


class Execution(BaseSettings):
    class Config:
        env_prefix = "LAMINAR_EXECUTION_"

    id: str = None


class Layer(BaseSettings):
    class Config:
        env_prefix = "LAMINAR_LAYER_"

    name: str = None


class Current:
    execution = setting(Execution)
    python = setting(Python)
    layer = setting(Layer)


current = Current()
