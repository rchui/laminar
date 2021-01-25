from typing import List

from fastapi import APIRouter

from laminar.api import models
from laminar.databases import postgres, schema

router = APIRouter(prefix="/steps")


@router.get("/")
def get_steps() -> List[models.Step]:
    """Get steps."""

    response: List[models.Step] = postgres.client.session().query(schema.Step).all()
    return response


@router.get("/{step}")
def get_step(step: int) -> models.Step:
    """Get a step."""

    response: models.Step = postgres.client.session().query(schema.Step).filter(schema.Step.id == step).one()
    return response
