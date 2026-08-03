"""Operator-approved, reality-facing validation experiments."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.dependencies import get_db
from apps.api.schemas.need_issue import (
    ExperimentApproval,
    ExperimentDecision,
    MarketObservationCreate,
    MarketObservationResponse,
    ValidationExecutionTaskCreate,
    ValidationExecutionTaskResponse,
    ValidationExperimentListResponse,
    ValidationExperimentResponse,
)
from packages.storage.models.need_issue import (
    MarketObservation,
    ValidationExecutionTask,
    ValidationExperiment,
)

router = APIRouter()


async def _experiment_or_404(db: AsyncSession, experiment_id: uuid.UUID) -> ValidationExperiment:
    experiment = await db.scalar(
        select(ValidationExperiment)
        .options(selectinload(ValidationExperiment.execution_tasks))
        .where(ValidationExperiment.id == experiment_id)
    )
    if experiment is None:
        raise HTTPException(status_code=404, detail="Validation experiment not found")
    return experiment


@router.get("", response_model=ValidationExperimentListResponse)
async def list_validation_experiments(
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(ValidationExperiment).options(selectinload(ValidationExperiment.execution_tasks))
    count_query = select(func.count(ValidationExperiment.id))
    if status is not None:
        query = query.where(ValidationExperiment.status == status)
        count_query = count_query.where(ValidationExperiment.status == status)
    total = await db.scalar(count_query) or 0
    experiments = await db.scalars(
        query.order_by(ValidationExperiment.updated_at.desc(), ValidationExperiment.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return ValidationExperimentListResponse(
        items=list(experiments), total=total, page=page, page_size=page_size
    )


@router.get("/{experiment_id}", response_model=ValidationExperimentResponse)
async def get_experiment(experiment_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    return await _experiment_or_404(db, experiment_id)


@router.post(
    "/{experiment_id}/execution-tasks",
    response_model=ValidationExecutionTaskResponse,
    status_code=201,
)
async def create_execution_task(
    experiment_id: uuid.UUID,
    body: ValidationExecutionTaskCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    experiment = await _experiment_or_404(db, experiment_id)
    if experiment.status not in {"draft", "approved"}:
        raise HTTPException(
            status_code=409, detail="Execution tasks can only be planned before contact work"
        )
    task = ValidationExecutionTask(experiment_id=experiment.id, **body.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.post(
    "/{experiment_id}/execution-tasks/{task_id}/mark-contacted",
    response_model=ValidationExecutionTaskResponse,
)
async def mark_execution_task_contacted(
    experiment_id: uuid.UUID,
    task_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    experiment = await _experiment_or_404(db, experiment_id)
    if experiment.status != "running":
        raise HTTPException(
            status_code=409,
            detail="External contact requires operator approval and a running experiment",
        )
    task = await db.get(ValidationExecutionTask, task_id)
    if task is None or task.experiment_id != experiment.id:
        raise HTTPException(status_code=404, detail="Validation execution task not found")
    if task.status != "planned":
        raise HTTPException(status_code=409, detail="Only a planned task can be marked contacted")
    task.status = "contacted"
    task.contacted_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(task)
    return task


@router.post("/{experiment_id}/approve", response_model=ValidationExperimentResponse)
async def approve_experiment(
    experiment_id: uuid.UUID,
    body: ExperimentApproval,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    experiment = await _experiment_or_404(db, experiment_id)
    if experiment.status != "draft":
        raise HTTPException(status_code=409, detail="Only a draft experiment can be approved")
    experiment.status = "approved"
    experiment.approval_note = body.operator_note
    await db.commit()
    await db.refresh(experiment)
    return experiment


@router.post("/{experiment_id}/start", response_model=ValidationExperimentResponse)
async def start_experiment(experiment_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    experiment = await _experiment_or_404(db, experiment_id)
    if experiment.requires_external_action and experiment.status != "approved":
        raise HTTPException(status_code=409, detail="External work requires operator approval")
    if not experiment.requires_external_action and experiment.status != "draft":
        raise HTTPException(status_code=409, detail="Only a draft experiment can be started")
    experiment.status = "running"
    await db.commit()
    await db.refresh(experiment)
    return experiment


@router.post(
    "/{experiment_id}/observations", response_model=MarketObservationResponse, status_code=201
)
async def record_market_observation(
    experiment_id: uuid.UUID,
    body: MarketObservationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    experiment = await _experiment_or_404(db, experiment_id)
    if experiment.status != "running":
        raise HTTPException(
            status_code=409, detail="Market observations require a running experiment"
        )
    observation = MarketObservation(experiment_id=experiment.id, **body.model_dump())
    db.add(observation)
    await db.commit()
    await db.refresh(observation)
    return observation


@router.post("/{experiment_id}/decision", response_model=ValidationExperimentResponse)
async def decide_experiment(
    experiment_id: uuid.UUID,
    body: ExperimentDecision,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    experiment = await _experiment_or_404(db, experiment_id)
    observations = await db.scalar(
        select(func.count(MarketObservation.id)).where(
            MarketObservation.experiment_id == experiment.id
        )
    )
    if not observations:
        raise HTTPException(
            status_code=409, detail="A decision requires at least one market observation"
        )
    if experiment.status not in {"draft", "approved", "running"}:
        raise HTTPException(
            status_code=409, detail="This experiment already has a closing decision"
        )
    experiment.status = "decided"
    experiment.decision = body.decision
    experiment.decision_rationale = body.rationale
    await db.commit()
    await db.refresh(experiment)
    return experiment
