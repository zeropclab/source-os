"""Product Thesis offers and their observable economic evidence."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from apps.api.schemas.need_issue import (
    BuildAuthorizationCreate,
    BuildAuthorizationResponse,
    ProductThesisDecision,
    ProductThesisObservationCreate,
    ProductThesisObservationResponse,
    ProductThesisResponse,
)
from packages.storage.models.need_issue import (
    BuildAuthorization,
    ProductThesis,
    ProductThesisObservation,
)

router = APIRouter()


async def _thesis_or_404(db: AsyncSession, thesis_id: uuid.UUID) -> ProductThesis:
    thesis = await db.get(ProductThesis, thesis_id)
    if thesis is None:
        raise HTTPException(status_code=404, detail="Product Thesis not found")
    return thesis


@router.post(
    "/{thesis_id}/observations", response_model=ProductThesisObservationResponse, status_code=201
)
async def record_observation(
    thesis_id: uuid.UUID,
    body: ProductThesisObservationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    thesis = await _thesis_or_404(db, thesis_id)
    if thesis.status == "decided":
        raise HTTPException(
            status_code=409, detail="A decided Product Thesis cannot receive new observations"
        )
    observation = ProductThesisObservation(product_thesis_id=thesis.id, **body.model_dump())
    db.add(observation)
    await db.commit()
    await db.refresh(observation)
    return observation


@router.post(
    "/{thesis_id}/build-authorization", response_model=BuildAuthorizationResponse, status_code=201
)
async def authorize_build(
    thesis_id: uuid.UUID,
    body: BuildAuthorizationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    thesis = await _thesis_or_404(db, thesis_id)
    if thesis.status != "decided" or thesis.decision != "continue":
        raise HTTPException(
            status_code=409,
            detail="A build authorization requires a continuing Product Thesis decision",
        )
    existing = await db.scalar(
        select(BuildAuthorization).where(BuildAuthorization.product_thesis_id == thesis.id)
    )
    if existing is not None:
        raise HTTPException(
            status_code=409, detail="This Product Thesis already has a build authorization"
        )
    authorization = BuildAuthorization(product_thesis_id=thesis.id, rationale=body.rationale)
    db.add(authorization)
    await db.commit()
    await db.refresh(authorization)
    return authorization


@router.post("/{thesis_id}/decision", response_model=ProductThesisResponse)
async def decide_thesis(
    thesis_id: uuid.UUID, body: ProductThesisDecision, db: Annotated[AsyncSession, Depends(get_db)]
):
    thesis = await _thesis_or_404(db, thesis_id)
    count = await db.scalar(
        select(func.count(ProductThesisObservation.id)).where(
            ProductThesisObservation.product_thesis_id == thesis.id
        )
    )
    if not count:
        raise HTTPException(
            status_code=409,
            detail="A Product Thesis decision requires at least one offer observation",
        )
    thesis.status = "decided"
    thesis.decision, thesis.decision_rationale = body.decision, body.rationale
    await db.commit()
    await db.refresh(thesis)
    return thesis
