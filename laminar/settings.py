"""Laminar flow configurations."""

import sys
from typing import Any, Type, TypeVar, cast

from pydantic import BaseSettings

T = TypeVar("T")


def setting(category: Type[T]) -> T:
    key = category.__name__.lower()  # type: ignore

    def setting_getter(self: Any, key: str = key) -> T:
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


class Pipeline(BaseSettings):
    class Config:
        env_prefix = "LAMINAR_PIPELINE_"

    name: str


class State(BaseSettings):
    class Config:
        env_prefix = "LAMINAR_STATE_"

    pipeline: bool = False
    step: bool = False


class Step(BaseSettings):
    class Config:
        env_prefix = "LAMINAR_STEP_"

    name: str


class Configuration:
    artifact = setting(Artifact)
    execution = setting(Execution)
    pipeline = setting(Pipeline)
    python = setting(Python)
    state = setting(State)
    step = setting(Step)
