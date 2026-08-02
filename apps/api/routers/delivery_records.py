"""Trace local or remote development delivery back to a Feature Definition."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from apps.api.schemas.need_issue import DeliveryRecordCreate, DeliveryRecordResponse
from packages.storage.models.need_issue import DeliveryRecord, FeatureDefinition

router = APIRouter()


@router.post(
    "/features/{feature_id}/deliveries", response_model=DeliveryRecordResponse, status_code=201
)
async def create_delivery(
    feature_id: uuid.UUID, body: DeliveryRecordCreate, db: Annotated[AsyncSession, Depends(get_db)]
):
    feature = await db.get(FeatureDefinition, feature_id)
    if feature is None:
        raise HTTPException(status_code=404, detail="Feature Definition not found")
    record = DeliveryRecord(feature_definition_id=feature.id, **body.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.post("/{delivery_id}/release", response_model=DeliveryRecordResponse)
async def release_delivery(delivery_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    record = await db.get(DeliveryRecord, delivery_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Delivery record not found")
    required = (
        "tests_evidence",
        "review_conclusion",
        "migration_evidence",
        "rollback_evidence",
        "acceptance_evidence",
        "tracking_evidence",
    )
    missing = [field for field in required if not getattr(record, field)]
    if missing:
        raise HTTPException(
            status_code=409, detail=f"Release evidence is incomplete: {', '.join(missing)}"
        )
    record.status, record.released_at = "released", datetime.now(UTC)
    await db.commit()
    await db.refresh(record)
    return record
