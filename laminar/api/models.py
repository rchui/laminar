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


class Task(BaseModel):
    name: str
    flow: int
    payload: Dict[str, Any]

    class Config:
        orm_mode = True


class Status(BaseModel):
    execution: int
    task: int
    status: str

    class Config:
        orm_mode = True
