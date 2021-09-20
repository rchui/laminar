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


class Artifact(BaseSettings):
    class Config:
        env_prefix = "LAMINAR_ARTIFACT_"

    source: str = ".laminar"


class Execution(BaseSettings):
    class Config:
        env_prefix = "LAMINAR_EXECUTION_"

    id: str


class Flow(BaseSettings):
    class Config:
        env_prefix = "LAMINAR_FLOW_"

    name: str


class Layer(BaseSettings):
    class Config:
        env_prefix = "LAMINAR_LAYER_"

    name: str


class Configuration:
    artifact = setting(Artifact)
    execution = setting(Execution)
    flow = setting(Flow)
    python = setting(Python)
    layer = setting(Layer)
