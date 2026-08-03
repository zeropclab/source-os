"""Create and read operator-bounded Discovery Objectives."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.dependencies import get_db
from apps.api.schemas.discovery_objective import (
    ApprovedCollectionBoundaryResponse,
    DiscoveryObjectiveCreate,
    DiscoveryObjectiveResponse,
    DiscoveryObjectiveWorkspaceResponse,
)
from packages.storage.models.discovery_objective import (
    ApprovedCollectionBoundary,
    DiscoveryObjective,
)
from packages.storage.models.source import Source

router = APIRouter()


def _objective_with_boundaries(objective_id: uuid.UUID):
    return (
        select(DiscoveryObjective)
        .options(selectinload(DiscoveryObjective.boundaries))
        .where(DiscoveryObjective.id == objective_id)
    )


def _response_for(objective: DiscoveryObjective) -> DiscoveryObjectiveResponse:
    current_boundary = objective.boundaries[-1]
    return DiscoveryObjectiveResponse(
        id=objective.id,
        title=objective.title,
        question=objective.question,
        resource_stop_conditions=objective.resource_stop_conditions,
        evidence_stop_conditions=objective.evidence_stop_conditions,
        decision_stop_conditions=objective.decision_stop_conditions,
        status=objective.status,
        created_at=objective.created_at,
        updated_at=objective.updated_at,
        current_boundary=ApprovedCollectionBoundaryResponse.model_validate(current_boundary),
    )


@router.post("", response_model=DiscoveryObjectiveResponse, status_code=201)
async def create_discovery_objective(
    body: DiscoveryObjectiveCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    source_ids = body.initial_boundary.approved_source_ids
    if len(set(source_ids)) != len(source_ids):
        raise HTTPException(status_code=422, detail="Approved source IDs must not repeat")

    found_source_ids = set(
        (await db.scalars(select(Source.id).where(Source.id.in_(source_ids)))).all()
    )
    if found_source_ids != set(source_ids):
        raise HTTPException(status_code=422, detail="An approved source does not exist")

    objective = DiscoveryObjective(
        title=body.title,
        question=body.question,
        resource_stop_conditions=body.resource_stop_conditions,
        evidence_stop_conditions=body.evidence_stop_conditions,
        decision_stop_conditions=body.decision_stop_conditions,
    )
    boundary = ApprovedCollectionBoundary(
        objective=objective,
        version=1,
        approved_source_ids=[str(source_id) for source_id in source_ids],
        tool_allowlist=body.initial_boundary.tool_allowlist,
        request_limit=body.initial_boundary.request_limit,
        time_budget_minutes=body.initial_boundary.time_budget_minutes,
        cost_budget_cents=body.initial_boundary.cost_budget_cents,
    )
    db.add_all([objective, boundary])
    await db.commit()
    saved = await db.scalar(_objective_with_boundaries(objective.id))
    return _response_for(saved)


@router.get("/{objective_id}", response_model=DiscoveryObjectiveResponse)
async def get_discovery_objective(
    objective_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    objective = await db.scalar(_objective_with_boundaries(objective_id))
    if objective is None:
        raise HTTPException(status_code=404, detail="Discovery Objective not found")
    return _response_for(objective)


@router.get("/{objective_id}/workspace", response_model=DiscoveryObjectiveWorkspaceResponse)
async def get_discovery_objective_workspace(
    objective_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    objective = await db.scalar(_objective_with_boundaries(objective_id))
    if objective is None:
        raise HTTPException(status_code=404, detail="Discovery Objective not found")
    response = _response_for(objective)
    return DiscoveryObjectiveWorkspaceResponse(
        objective=response,
        current_boundary=response.current_boundary,
    )
