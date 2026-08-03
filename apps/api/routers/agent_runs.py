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
from packages.storage.models.discovery_objective import (
    ApprovedCollectionBoundary,
    DiscoveryObjective,
)
from packages.storage.models.external_signal import ExternalSignal

router = APIRouter()
objective_router = APIRouter()
_TOOL_ALLOWLIST: list[str] = []


def _objective_input_context(
    objective: DiscoveryObjective, boundary: ApprovedCollectionBoundary
) -> dict:
    """Freeze the read-only Objective and Boundary the Agent was allowed to see."""
    return {
        "objective": {
            "id": str(objective.id),
            "title": objective.title,
            "question": objective.question,
            "status": objective.status,
            "resource_stop_conditions": objective.resource_stop_conditions,
            "evidence_stop_conditions": objective.evidence_stop_conditions,
            "decision_stop_conditions": objective.decision_stop_conditions,
        },
        "boundary": {
            "id": str(boundary.id),
            "version": boundary.version,
            "approved_source_ids": boundary.approved_source_ids,
            "tool_allowlist": boundary.tool_allowlist,
            "request_limit": boundary.request_limit,
            "time_budget_minutes": boundary.time_budget_minutes,
            "cost_budget_cents": boundary.cost_budget_cents,
            "credential_scope": boundary.credential_scope,
            "evidence_conditions": boundary.evidence_conditions,
        },
    }


async def _run_or_404(db: AsyncSession, run_id: uuid.UUID) -> AgentRun:
    run = await db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Agent Run not found")
    return run


def _bundle_hash(bundle: object) -> str:
    encoded = json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _structured_assessment_proposal(runtime_output: dict, evidence_ids: list[str]) -> dict:
    """Expose a stable proposal contract; malformed model text becomes an explicit unknown."""
    fallback = {
        "contract": "discovery_assessment_proposal.v1",
        "kind": "unknown",
        "statement": "The Agent output cannot support an assessment proposal yet.",
        "evidence_ids": evidence_ids,
        "assessment_ids": [],
        "unknowns": ["Pi output did not satisfy the assessment proposal contract."],
        "coverage_gaps": [],
        "recommendation": "Review the cited evidence or run a bounded next acquisition plan.",
        "status": "unknown",
    }
    try:
        raw = json.loads(str(runtime_output.get("raw_output", "")))
    except json.JSONDecodeError:
        return fallback
    allowed_kinds = {
        "support",
        "counterevidence",
        "unknown",
        "coverage_gap",
        "blocked",
        "recommendation",
    }
    if (
        not isinstance(raw, dict)
        or raw.get("kind") not in allowed_kinds
        or not isinstance(raw.get("statement"), str)
        or not raw["statement"].strip()
        or not isinstance(raw.get("unknowns", []), list)
    ):
        return fallback
    cited_ids = raw.get("evidence_ids", evidence_ids)
    if not isinstance(cited_ids, list) or set(cited_ids) - set(evidence_ids):
        return fallback
    return {
        "contract": "discovery_assessment_proposal.v1",
        "kind": raw["kind"],
        "statement": raw["statement"].strip(),
        "evidence_ids": cited_ids,
        "assessment_ids": [],
        "unknowns": raw.get("unknowns", []),
        "coverage_gaps": raw.get("coverage_gaps", []),
        "recommendation": raw.get("recommendation"),
        "status": "proposed",
    }


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


@objective_router.post(
    "/{objective_id}/agent-runs", response_model=AgentRunResponse, status_code=201
)
async def create_objective_agent_run(
    objective_id: uuid.UUID,
    body: AgentRunCreate,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    objective = await db.get(DiscoveryObjective, objective_id)
    if objective is None:
        raise HTTPException(status_code=404, detail="Discovery Objective not found")
    if objective.status != "active":
        raise HTTPException(
            status_code=409, detail="Only an active objective can run the Discovery Agent"
        )
    boundary = await db.scalar(
        select(ApprovedCollectionBoundary)
        .where(ApprovedCollectionBoundary.objective_id == objective_id)
        .order_by(ApprovedCollectionBoundary.version.desc())
    )
    if (
        body.max_tool_calls > boundary.request_limit
        or body.max_cost_cents > boundary.cost_budget_cents
    ):
        raise HTTPException(status_code=422, detail="Agent budget is outside the approved boundary")
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
    if len(signals) != len(body.evidence_signal_ids):
        raise HTTPException(status_code=422, detail="Every evidence signal must exist")
    bundle = [
        {
            "signal_id": str(signal.id),
            "source_label": signal.source_label,
            "source_uri": signal.source_uri,
            "original_material": signal.original_material,
            "observation": signal.observation,
        }
        for signal in signals
    ]
    input_context = _objective_input_context(objective, boundary)
    run = AgentRun(
        objective_id=objective_id,
        boundary_id=boundary.id,
        boundary_version=boundary.version,
        input_context=input_context,
        idempotency_key=body.idempotency_key,
        task_instruction=body.task_instruction,
        evidence_bundle=bundle,
        evidence_bundle_hash=_bundle_hash({"input_context": input_context, "evidence": bundle}),
        model_version=body.model_version,
        prompt_version=body.prompt_version,
        budgets={
            "max_tool_calls": body.max_tool_calls,
            "max_tokens": body.max_tokens,
            "max_cost_cents": body.max_cost_cents,
        },
        tool_allowlist=boundary.tool_allowlist,
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
    if run.objective_id is not None:
        objective = await db.get(DiscoveryObjective, run.objective_id)
        current_boundary = await db.scalar(
            select(ApprovedCollectionBoundary)
            .where(ApprovedCollectionBoundary.objective_id == run.objective_id)
            .order_by(ApprovedCollectionBoundary.version.desc())
        )
        if (
            objective is None
            or objective.status != "active"
            or current_boundary is None
            or current_boundary.id != run.boundary_id
            or current_boundary.version != run.boundary_version
        ):
            raise HTTPException(
                status_code=409,
                detail="Discovery Agent run boundary is no longer active",
            )
    try:
        runtime_output = await run_pi_proposal(
            run_id=str(run.id),
            task_instruction=run.task_instruction,
            evidence_bundle_hash=run.evidence_bundle_hash,
            evidence_bundle=(
                [*run.evidence_bundle, {"kind": "objective_context", "snapshot": run.input_context}]
                if run.input_context is not None
                else run.evidence_bundle
            ),
            model_version=run.model_version,
            budgets=run.budgets,
        )
        runtime_usage = runtime_output.pop("usage", {})
        if run.objective_id is not None:
            runtime_output["proposal"] = _structured_assessment_proposal(
                runtime_output,
                [entry["signal_id"] for entry in run.evidence_bundle],
            )
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
