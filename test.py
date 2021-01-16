from typing import Any, Dict

from laminar.components import Flow
from laminar.schedulers import Scheduler

flow = Flow("test", Scheduler("test-queue"))


@flow.step()
def end(a: int, b: str, c: bool) -> Dict[str, Any]:
    print("Inheriting a from branch_1, b from branch_2, c from start_2", c)
    return {}


@flow.step(end)
def start_2(c: float) -> Dict[str, Any]:
    print("Inheriting c from flow", c)
    return {"c": True}


@flow.step(end)
def branch_2(b: str) -> Dict[str, Any]:
    print("Inheriting b from start_1", b)
    return {"b": b}


@flow.step(end)
def branch_1(a: int) -> Dict[str, Any]:
    print("Inheriting a from start_2", a)
    return {"a": int}


@flow.step(branch_1, branch_2)
def start_1(start: str) -> Dict[str, Any]:
    print("Inheriting start from flow", start)
    return {"a": 5, "b": "b"}


if __name__ == "__main__":
    flow(start="hello world", c=1.25)
