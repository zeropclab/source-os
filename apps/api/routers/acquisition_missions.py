"""Create and retrieve bounded Acquisition Mission drafts."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from apps.api.dependencies import get_db
from apps.api.schemas.acquisition_mission import (
    AcquisitionMissionCreate,
    AcquisitionMissionListResponse,
    AcquisitionMissionResponse,
)
from packages.storage.models.acquisition_mission import AcquisitionMission
from packages.storage.models.acquisition_plan import AcquisitionPlan
from packages.storage.models.discovery_objective import (
    ApprovedCollectionBoundary,
    DiscoveryObjective,
)
from packages.storage.models.source_config_version import SourceConfigVersion

router = APIRouter()


def _mission_with_pinned_config(mission_id: uuid.UUID):
    return (
        select(AcquisitionMission)
        .options(joinedload(AcquisitionMission.source_config_version))
        .where(AcquisitionMission.id == mission_id)
    )


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

    if body.acquisition_plan_id is not None:
        plan = await db.scalar(
            select(AcquisitionPlan).where(AcquisitionPlan.id == body.acquisition_plan_id)
        )
        if plan is None or str(body.source_id) not in plan.selected_source_ids:
            raise HTTPException(
                status_code=422,
                detail="Mission source is not selected by the plan",
            )
        objective = await db.scalar(
            select(DiscoveryObjective).where(DiscoveryObjective.id == plan.objective_id)
        )
        current_boundary = await db.scalar(
            select(ApprovedCollectionBoundary)
            .where(ApprovedCollectionBoundary.objective_id == plan.objective_id)
            .order_by(ApprovedCollectionBoundary.version.desc())
        )
        if objective.status != "active" or plan.boundary_id != current_boundary.id:
            raise HTTPException(
                status_code=409,
                detail="Plan is no longer permitted by the current approved boundary",
            )

    mission = AcquisitionMission(
        **body.model_dump(),
        source_config_version=config,
    )
    db.add(mission)
    await db.commit()
    return await db.scalar(_mission_with_pinned_config(mission.id))


@router.get("", response_model=AcquisitionMissionListResponse)
async def list_acquisition_missions(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    total = await db.scalar(select(func.count(AcquisitionMission.id))) or 0
    missions = await db.scalars(
        select(AcquisitionMission)
        .options(joinedload(AcquisitionMission.source_config_version))
        .order_by(AcquisitionMission.updated_at.desc(), AcquisitionMission.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return AcquisitionMissionListResponse(
        items=list(missions.unique()), total=total, page=page, page_size=page_size
    )


@router.get("/{mission_id}", response_model=AcquisitionMissionResponse)
async def get_acquisition_mission(
    mission_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    mission = await db.scalar(_mission_with_pinned_config(mission_id))
    if mission is None:
        raise HTTPException(status_code=404, detail="Acquisition Mission not found")
    return mission
