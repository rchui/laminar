from typing import List

from fastapi import APIRouter

from laminar.api import models
from laminar.databases import postgres, schema

router = APIRouter(prefix="/tasks")


@router.get("/")
def get_tasks() -> List[models.Task]:
    """Get tasks."""

    response: List[models.Task] = postgres.client.session().query(schema.Task).all()
    return response


@router.get("/{task}")
def get_task(task: int) -> models.Task:
    """Get a task."""

    response: models.Task = postgres.client.session().query(schema.Task).filter(schema.Task.id == task).one()
    return response
