"""Global configs for laminar flows."""

from pydantic import BaseSettings, Field


class Execution(BaseSettings):
    agent: bool = Field(False, env="LAMINAR_EXECUTION_AGENT")
    step: str = Field(None, env="LAMINAR_EXECUTION_STEP")


class Workspace(BaseSettings):
    path: str = Field(None, env="LAMINAR_WORKSPACE_PATH")


execution = Execution()
workspace = Workspace()
