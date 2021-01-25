from typing import List

from fastapi import APIRouter, status

from laminar.api import models
from laminar.databases import postgres, schema

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
        postgres.client.session()
        .query(schema.Flow, schema.Execution)
        .filter(schema.Flow.id == schema.Execution.flow)
        .filter(schema.Flow.id == flow)
        .all()
    )
    return response


@router.get("/{flow}/executions/{execution}")
def get_execution(flow: int, execution: int) -> models.Execution:
    """Get an execution for a flow."""

    response: models.Execution = (
        postgres.client.session()
        .query(schema.Flow, schema.Execution)
        .filter(schema.Flow.id == schema.Execution.flow)
        .filter(schema.Flow.id == flow)
        .filter(schema.Execution.id == execution)
        .one()
    )
    return response


@router.get("/{flow}/steps")
def get_steps(flow: int) -> List[models.Step]:
    """Get steps for a flow."""

    response: List[models.Step] = (
        postgres.client.session()
        .query(schema.Flow, schema.Step)
        .filter(schema.Flow.id == schema.Step.flow)
        .filter(schema.Flow.id == flow)
        .all()
    )
    return response


@router.get("/{flow}/steps/{step}")
def get_step(flow: int, step: int) -> models.Step:
    """Get a step for a flow."""

    response: models.Step = (
        postgres.client.session()
        .query(schema.Flow, schema.Step)
        .filter(schema.Flow.id == schema.Step.id)
        .filter(schema.Flow.id == flow)
        .filter(schema.Step.id == step)
        .one()
    )
    return response
