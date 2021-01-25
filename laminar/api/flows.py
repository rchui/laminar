import logging
from typing import List

from fastapi import APIRouter, status

from laminar.api import models
from laminar.databases import postgres, schema

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/flows")


@router.get("/")
def get_flows() -> List[models.Flow]:
    """Get all flows."""

    response: List[models.Flow] = postgres.client.session().query(schema.Flow).all()
    return response


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_flow(flow: models.Flow) -> models.Flow:
    """Create a flow."""

    flow = schema.Flow(name=flow.name, project=flow.project)
    session = postgres.client.session()
    session.add(flow)
    session.commit()
    session.refresh(flow)
    return flow


@router.get("/{flow}")
def get_flow(flow: int) -> models.Flow:
    """Get a flow."""

    response: models.Flow = postgres.client.session().query(schema.Flow).filter(schema.Flow.id == flow).one()
    return response


@router.get("/{flow}/executions")
def get_executions(flow: int) -> List[models.Execution]:
    """Get executions for a flow."""

    response: List[models.Execution] = (
        postgres.client.session().query(schema.Execution).join(schema.Flow).filter(schema.Flow.id == flow).all()
    )
    return response


@router.get("/{flow}/executions/{execution}")
def get_execution(flow: int, execution: int) -> models.Execution:
    """Get an execution for a flow."""

    response: models.Execution = (
        postgres.client.session()
        .query(schema.Execution)
        .join(schema.Flow)
        .filter(schema.Flow.id == flow)
        .filter(schema.Execution.id == execution)
        .one()
    )
    return response


@router.get("/{flow}/tasks")
def get_tasks(flow: int) -> List[models.Task]:
    """Get tasks for a flow."""

    response: List[models.Task] = (
        postgres.client.session().query(schema.Task).join(schema.Flow).filter(schema.Flow.id == flow).all()
    )
    return response


@router.get("/{flow}/tasks/{task}")
def get_task(flow: int, task: int) -> models.Task:
    """Get a task for a flow."""

    response: models.Task = (
        postgres.client.session()
        .query(schema.Task)
        .join(schema.Flow)
        .filter(schema.Flow.id == flow)
        .filter(schema.Task.id == task)
        .one()
    )
    return response
