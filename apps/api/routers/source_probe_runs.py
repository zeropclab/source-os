"""Run and retrieve bounded probes of immutable source configurations."""

import asyncio
import time
import uuid
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db, get_source_probe_adapter
from apps.api.schemas.source_probe_run import SourceProbeRunCreate, SourceProbeRunResponse
from packages.adapters.source_probe import (
    AccessState,
    ProbeExecution,
    ProbeRequestBudgetExceededError,
    ProbeResult,
    SourceProbeAdapter,
)
from packages.storage.models.source import Source
from packages.storage.models.source_config_version import SourceConfigVersion
from packages.storage.models.source_probe_run import SourceProbeRun

router = APIRouter()
read_router = APIRouter()


def _assert_adapter_contract(result: ProbeResult) -> None:
    if result.status == "succeeded" and result.sample is None:
        raise HTTPException(
            status_code=502, detail="Probe adapter reported success without a sample"
        )


def _failed_probe_result(
    access_state: AccessState,
    *,
    context_risk: str,
    outcome_detail: str,
) -> ProbeResult:
    return ProbeResult(
        status="failed",
        access_state=access_state,
        sample=None,
        pagination_supported=None,
        replies_supported=None,
        context_risks=[context_risk],
        outcome_detail=outcome_detail,
    )


@router.post(
    "/{source_id}/config-versions/{version}/probes",
    response_model=SourceProbeRunResponse,
    status_code=201,
)
async def create_source_probe_run(
    source_id: uuid.UUID,
    version: int,
    body: SourceProbeRunCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    adapter: Annotated[SourceProbeAdapter, Depends(get_source_probe_adapter)],
):
    config = await db.scalar(
        select(SourceConfigVersion).where(
            SourceConfigVersion.source_id == source_id,
            SourceConfigVersion.version == version,
        )
    )
    if config is None:
        raise HTTPException(status_code=404, detail="Source configuration version not found")

    configured_request_limit = config.request_policy["request_limit"]
    configured_timeout = config.request_policy["timeout_seconds"]
    if body.request_budget > configured_request_limit:
        raise HTTPException(
            status_code=422,
            detail="Probe request budget exceeds the immutable source configuration limit",
        )
    if body.time_budget_seconds > configured_timeout:
        raise HTTPException(
            status_code=422,
            detail="Probe time budget exceeds the immutable source configuration limit",
        )

    source = await db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    execution = ProbeExecution(
        request_limit=body.request_budget,
        time_limit_seconds=body.time_budget_seconds,
    )
    started_at = time.monotonic()
    try:
        async with asyncio.timeout(body.time_budget_seconds):
            result = await adapter.probe(source, config, execution=execution)
    except ProbeRequestBudgetExceededError:
        result = _failed_probe_result(
            cast(AccessState, config.access_mode),
            context_risk="Probe exhausted its request budget before completion.",
            outcome_detail="request_budget_exhausted",
        )
    except TimeoutError:
        result = _failed_probe_result(
            cast(AccessState, config.access_mode),
            context_risk="Probe timed out before source capabilities were verified.",
            outcome_detail="probe_timeout",
        )
    else:
        _assert_adapter_contract(result)
    elapsed_ms = int((time.monotonic() - started_at) * 1000)
    run = SourceProbeRun(
        source_config_version_id=config.id,
        **body.model_dump(),
        status=result.status,
        access_state=result.access_state,
        sample_available=result.sample is not None,
        sample=result.sample,
        pagination_supported=result.pagination_supported,
        replies_supported=result.replies_supported,
        context_risks=result.context_risks,
        consumed_requests=execution.consumed_requests,
        elapsed_ms=elapsed_ms,
        outcome_detail=result.outcome_detail,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


@read_router.get("/{probe_id}", response_model=SourceProbeRunResponse)
async def get_source_probe_run(
    probe_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    run = await db.get(SourceProbeRun, probe_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Source probe not found")
    return run
