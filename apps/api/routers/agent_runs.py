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
from packages.storage.models.agent_run import AgentRun
from packages.storage.models.external_signal import ExternalSignal

router = APIRouter()
_TOOL_ALLOWLIST = ["retrieve_evidence", "find_counterevidence"]


async def _run_or_404(db: AsyncSession, run_id: uuid.UUID) -> AgentRun:
    run = await db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Agent Run not found")
    return run


def _bundle_hash(bundle: list[dict]) -> str:
    encoded = json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _proposal(bundle: list[dict]) -> dict:
    citations = [entry["signal_id"] for entry in bundle]
    first = bundle[0]
    return {
        "kind": "need_issue_proposal",
        "proposed_status": "captured",
        "actor": "unknown — proposal requires operator review",
        "problem": first["observation"],
        "desired_outcome": "unknown — requires a real validation action",
        "supporting_refs": citations[:1],
        "counter_refs": citations[1:],
        "citations": citations,
        "unknowns": [
            "Independence, prevalence, willingness to pay, and delivery feasibility are unknown."
        ],
        "competing_explanations": [
            "The reported workaround may be a one-off or already solved by existing tools."
        ],
        "next_validation_action": (
            "Ask one target actor for a concrete recent example and a counterexample."
        ),
        "cannot_conclude": (
            "This proposal is not a validated need, market size, or business decision."
        ),
    }


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
    tool_calls = min(len(run.evidence_bundle), run.budgets["max_tool_calls"])
    run.tool_audit = [
        {"tool": "retrieve_evidence", "signal_id": item["signal_id"], "status": "completed"}
        for item in run.evidence_bundle[:tool_calls]
    ]
    run.usage = {
        "tool_calls": tool_calls,
        "tokens": min(run.budgets["max_tokens"], 100 * tool_calls),
        "cost_cents": min(run.budgets["max_cost_cents"], tool_calls),
    }
    run.output = _proposal(run.evidence_bundle)
    run.status = "completed"
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
