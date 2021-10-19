from typing import Optional

from pydantic import BaseSettings


class Execution(BaseSettings):
    class Config:
        env_prefix = "LAMINAR_EXECUTION_"

    id: Optional[str] = None


class Flow(BaseSettings):
    class Config:
        env_prefix = "LAMINAR_FLOW_"

    name: Optional[str] = None


class Layer(BaseSettings):
    class Config:
        env_prefix = "LAMINAR_LAYER_"

    name: Optional[str] = None


class Current(BaseSettings):
    execution = Execution()
    flow = Flow()
    layer = Layer()


current = Current()
