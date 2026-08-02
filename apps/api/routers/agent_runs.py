"""Run deterministic proposal agents against an immutable evidence bundle."""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from apps.api.schemas.agent_run import AgentRunCreate, AgentRunOperatorDecision, AgentRunResponse
from apps.api.services.pi_runtime import PiRuntimeError, run_pi_proposal
from packages.storage.models.agent_run import AgentRun
from packages.storage.models.external_signal import ExternalSignal

router = APIRouter()
_TOOL_ALLOWLIST: list[str] = []


async def _run_or_404(db: AsyncSession, run_id: uuid.UUID) -> AgentRun:
    run = await db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Agent Run not found")
    return run


def _bundle_hash(bundle: list[dict]) -> str:
    encoded = json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


@router.get("/{run_id}", response_model=AgentRunResponse)
async def get_agent_run(run_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    return await _run_or_404(db, run_id)


@router.post("", response_model=AgentRunResponse, status_code=201)
async def create_agent_run(
    body: AgentRunCreate,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    existing = await db.scalar(
        select(AgentRun).where(AgentRun.idempotency_key == body.idempotency_key)
    )
    if existing is not None:
        response.status_code = 200
        return existing
    signals = list(
        await db.scalars(
            select(ExternalSignal).where(ExternalSignal.id.in_(body.evidence_signal_ids))
        )
    )
    by_id = {signal.id: signal for signal in signals}
    if len(by_id) != len(body.evidence_signal_ids):
        raise HTTPException(status_code=422, detail="Every evidence signal must exist")
    bundle = [
        {
            "signal_id": str(signal_id),
            "source_label": by_id[signal_id].source_label,
            "source_uri": by_id[signal_id].source_uri,
            "original_material": by_id[signal_id].original_material,
            "observation": by_id[signal_id].observation,
        }
        for signal_id in body.evidence_signal_ids
    ]
    run = AgentRun(
        idempotency_key=body.idempotency_key,
        task_instruction=body.task_instruction,
        evidence_bundle=bundle,
        evidence_bundle_hash=_bundle_hash(bundle),
        model_version=body.model_version,
        prompt_version=body.prompt_version,
        budgets={
            "max_tool_calls": body.max_tool_calls,
            "max_tokens": body.max_tokens,
            "max_cost_cents": body.max_cost_cents,
        },
        tool_allowlist=_TOOL_ALLOWLIST,
        tool_audit=[],
        usage={"tool_calls": 0, "tokens": 0, "cost_cents": 0},
        errors=[],
        operator_changes=[],
        status="created",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


@router.post("/{run_id}/execute", response_model=AgentRunResponse)
async def execute_agent_run(run_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    run = await _run_or_404(db, run_id)
    if run.status == "cancelled":
        raise HTTPException(status_code=409, detail="Cancelled Agent Run cannot execute")
    if run.status == "completed":
        return run
    try:
        runtime_output = await run_pi_proposal(
            run_id=str(run.id),
            task_instruction=run.task_instruction,
            evidence_bundle_hash=run.evidence_bundle_hash,
            evidence_bundle=run.evidence_bundle,
            model_version=run.model_version,
            budgets=run.budgets,
        )
        runtime_usage = runtime_output.pop("usage", {})
        run.output = runtime_output
        run.tool_audit = [
            {"tool": "Pi Agent", "status": "completed", "policy": "no executable tools"}
        ]
        run.usage = {
            "tool_calls": 0,
            "tokens": runtime_usage.get("tokens", 0),
            "cost_cents": runtime_usage.get("cost_cents", 0),
        }
        run.status = "completed"
    except PiRuntimeError as error:
        run.errors = [*run.errors, {"stage": "runtime", "error": str(error)}]
        run.status = "failed"
    run.completed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(run)
    return run


@router.post("/{run_id}/cancel", response_model=AgentRunResponse)
async def cancel_agent_run(run_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    run = await _run_or_404(db, run_id)
    if run.status == "completed":
        raise HTTPException(status_code=409, detail="Completed Agent Run cannot be cancelled")
    run.status = "cancelled"
    run.completed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(run)
    return run


@router.post("/{run_id}/operator-decisions", response_model=AgentRunResponse)
async def record_operator_decision(
    run_id: uuid.UUID,
    body: AgentRunOperatorDecision,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    run = await _run_or_404(db, run_id)
    if run.status != "completed":
        raise HTTPException(status_code=409, detail="Only a completed Agent Run can be reviewed")
    run.operator_changes = [
        *run.operator_changes,
        {"decision": body.decision, "reason": body.reason, "changes": body.changes},
    ]
    await db.commit()
    await db.refresh(run)
    return run
