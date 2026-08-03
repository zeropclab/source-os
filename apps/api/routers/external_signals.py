"""Capture immutable manual reality signals and triage them in the Evidence Inbox."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.dependencies import get_db
from apps.api.schemas.external_signal import (
    EvidenceInboxResponse,
    ExternalSignalCreate,
    ExternalSignalResponse,
    SignalTriageCreate,
)
from packages.storage.models.external_signal import ExternalSignal, SignalTriageEvent
from packages.storage.models.source import Source

router = APIRouter()
inbox_router = APIRouter()


async def _get_signal_or_404(db: AsyncSession, signal_id: uuid.UUID) -> ExternalSignal:
    result = await db.execute(
        select(ExternalSignal)
        .options(
            selectinload(ExternalSignal.triage_events),
            selectinload(ExternalSignal.mission_run_links),
        )
        .where(ExternalSignal.id == signal_id)
    )
    signal = result.scalar_one_or_none()
    if signal is None:
        raise HTTPException(status_code=404, detail="External signal not found")
    return signal


@router.post("", response_model=ExternalSignalResponse, status_code=201)
async def create_external_signal(
    body: ExternalSignalCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if body.source_id is not None and await db.get(Source, body.source_id) is None:
        raise HTTPException(status_code=422, detail="External Signal source does not exist")
    signal = ExternalSignal(**body.model_dump())
    db.add(signal)
    await db.commit()
    return await _get_signal_or_404(db, signal.id)


@router.get("/{signal_id}", response_model=ExternalSignalResponse)
async def get_external_signal(
    signal_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await _get_signal_or_404(db, signal_id)


@router.post("/{signal_id}/triage", response_model=ExternalSignalResponse)
async def triage_external_signal(
    signal_id: uuid.UUID,
    body: SignalTriageCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    signal = await _get_signal_or_404(db, signal_id)
    signal.status = body.status
    db.add(SignalTriageEvent(signal_id=signal.id, **body.model_dump()))
    await db.commit()
    return await _get_signal_or_404(db, signal.id)


@inbox_router.get("", response_model=EvidenceInboxResponse)
async def list_evidence_inbox(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(ExternalSignal)
        .options(
            selectinload(ExternalSignal.triage_events),
            selectinload(ExternalSignal.mission_run_links),
        )
        .where(ExternalSignal.status == "candidate")
        .order_by(ExternalSignal.captured_at.desc())
    )
    return EvidenceInboxResponse(items=list(result.scalars()))
