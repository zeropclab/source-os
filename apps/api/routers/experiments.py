"""Operator-approved, reality-facing validation experiments."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from apps.api.schemas.need_issue import (
    ExperimentApproval,
    ExperimentDecision,
    MarketObservationCreate,
    MarketObservationResponse,
    ValidationExperimentResponse,
)
from packages.storage.models.need_issue import MarketObservation, ValidationExperiment

router = APIRouter()


async def _experiment_or_404(db: AsyncSession, experiment_id: uuid.UUID) -> ValidationExperiment:
    experiment = await db.get(ValidationExperiment, experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="Validation experiment not found")
    return experiment


@router.get("/{experiment_id}", response_model=ValidationExperimentResponse)
async def get_experiment(experiment_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    return await _experiment_or_404(db, experiment_id)


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
