from typing import Optional

from pydantic import BaseModel, BaseSettings


class Current(BaseModel):
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

        index: Optional[int] = None
        name: Optional[str] = None

    execution = Execution()
    flow = Flow()
    layer = Layer()


current = Current()
