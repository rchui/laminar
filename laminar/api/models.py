from typing import Any, Dict

from pydantic import BaseModel


class Flow(BaseModel):
    name: str
    project: str

    class Config:
        orm_mode = True


class Execution(BaseModel):
    name: str
    flow: int

    class Config:
        orm_mode = True


class Step(BaseModel):
    name: str
    execution: int
    payload: Dict[str, Any]

    class Config:
        orm_mode = True


class Status(BaseModel):
    execution: int
    step: int
    status: str

    class Config:
        orm_mode = True
