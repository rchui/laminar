from typing import List

from fastapi import APIRouter

from laminar.api import models
from laminar.databases import postgres, schema

router = APIRouter(prefix="/executions")


@router.get("/")
def get_executions() -> List[models.Execution]:
    """Get executions."""

    response: List[models.Execution] = postgres.client.session().query(schema.Execution).all()
    return response


@router.get("/{execution}")
def get_execution(execution: int) -> models.Execution:
    """Get an execution."""

    response: models.Execution = (
        postgres.client.session().query(schema.Execution).filter(schema.Execution.id == execution).one()
    )
    return response
