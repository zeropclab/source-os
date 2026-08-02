"""Post-release outcome evidence."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from apps.api.schemas.need_issue import (
    FeatureOutcomeCreate,
    FeatureOutcomeResponse,
    OutcomeDecisionCreate,
)
from packages.storage.models.need_issue import DeliveryRecord, FeatureOutcome, OutcomeDecision

router = APIRouter()


async def _released_or_404(db: AsyncSession, delivery_id: uuid.UUID) -> DeliveryRecord:
    delivery = await db.get(DeliveryRecord, delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Delivery record not found")
    if delivery.status != "released":
        raise HTTPException(status_code=409, detail="Outcomes require a released delivery record")
    return delivery


@router.post(
    "/deliveries/{delivery_id}/outcomes", response_model=FeatureOutcomeResponse, status_code=201
)
async def record_outcome(
    delivery_id: uuid.UUID, body: FeatureOutcomeCreate, db: Annotated[AsyncSession, Depends(get_db)]
):
    delivery = await _released_or_404(db, delivery_id)
    outcome = FeatureOutcome(delivery_record_id=delivery.id, **body.model_dump())
    db.add(outcome)
    await db.commit()
    await db.refresh(outcome)
    return outcome


@router.post("/deliveries/{delivery_id}/decision")
async def decide_outcome(
    delivery_id: uuid.UUID,
    body: OutcomeDecisionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    delivery = await _released_or_404(db, delivery_id)
    count = await db.scalar(
        select(func.count(FeatureOutcome.id)).where(
            FeatureOutcome.delivery_record_id == delivery.id
        )
    )
    if not count:
        raise HTTPException(
            status_code=409, detail="An outcome decision requires at least one recorded outcome"
        )
    existing = await db.scalar(
        select(OutcomeDecision).where(OutcomeDecision.delivery_record_id == delivery.id)
    )
    if existing:
        raise HTTPException(status_code=409, detail="This delivery already has an outcome decision")
    decision = OutcomeDecision(delivery_record_id=delivery.id, **body.model_dump())
    db.add(decision)
    await db.commit()
    await db.refresh(decision)
    return decision
