"""Create and retrieve bounded Acquisition Mission drafts."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from apps.api.schemas.acquisition_mission import (
    AcquisitionMissionCreate,
    AcquisitionMissionResponse,
)
from packages.storage.models.acquisition_mission import AcquisitionMission

router = APIRouter()


@router.post("", response_model=AcquisitionMissionResponse, status_code=201)
async def create_acquisition_mission(
    body: AcquisitionMissionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    mission = AcquisitionMission(**body.model_dump())
    db.add(mission)
    await db.commit()
    await db.refresh(mission)
    return mission


@router.get("/{mission_id}", response_model=AcquisitionMissionResponse)
async def get_acquisition_mission(
    mission_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(AcquisitionMission).where(AcquisitionMission.id == mission_id))
    mission = result.scalar_one_or_none()
    if mission is None:
        raise HTTPException(status_code=404, detail="Acquisition Mission not found")
    return mission
