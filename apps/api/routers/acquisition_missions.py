"""Create and retrieve bounded Acquisition Mission drafts."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from apps.api.dependencies import get_db
from apps.api.schemas.acquisition_mission import (
    AcquisitionMissionCreate,
    AcquisitionMissionResponse,
)
from packages.storage.models.acquisition_mission import AcquisitionMission
from packages.storage.models.source_config_version import SourceConfigVersion

router = APIRouter()


@router.post("", response_model=AcquisitionMissionResponse, status_code=201)
async def create_acquisition_mission(
    body: AcquisitionMissionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    config = await db.scalar(
        select(SourceConfigVersion).where(
            SourceConfigVersion.id == body.source_config_version_id,
            SourceConfigVersion.source_id == body.source_id,
        )
    )
    if config is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "Source configuration version is missing or does not belong to the selected source"
            ),
        )
    if config.access_mode in {"blocked", "unsupported"}:
        raise HTTPException(
            status_code=422,
            detail=(
                "Source configuration version cannot run a mission while access mode is "
                f"{config.access_mode}"
            ),
        )

    mission = AcquisitionMission(
        **body.model_dump(),
        source_config_version=config,
    )
    db.add(mission)
    await db.commit()
    await db.refresh(mission)
    return mission


@router.get("/{mission_id}", response_model=AcquisitionMissionResponse)
async def get_acquisition_mission(
    mission_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(AcquisitionMission)
        .options(joinedload(AcquisitionMission.source_config_version))
        .where(AcquisitionMission.id == mission_id)
    )
    mission = result.scalar_one_or_none()
    if mission is None:
        raise HTTPException(status_code=404, detail="Acquisition Mission not found")
    return mission
