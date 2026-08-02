"""Falsifiable ontology hypotheses, never promoted needs."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from apps.api.schemas.need_issue import OntologyHypothesisCreate, OntologyHypothesisResponse
from packages.storage.models.need_issue import OntologyHypothesis

router = APIRouter()


@router.post("", response_model=OntologyHypothesisResponse, status_code=201)
async def create_hypothesis(
    body: OntologyHypothesisCreate, db: Annotated[AsyncSession, Depends(get_db)]
):
    hypothesis = OntologyHypothesis(**body.model_dump())
    db.add(hypothesis)
    await db.commit()
    await db.refresh(hypothesis)
    return hypothesis


@router.get("")
async def list_hypotheses(db: Annotated[AsyncSession, Depends(get_db)]):
    hypotheses = await db.scalars(
        select(OntologyHypothesis).order_by(OntologyHypothesis.created_at.desc())
    )
    return {"items": list(hypotheses)}
