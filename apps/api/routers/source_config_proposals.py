"""Pi-assisted configuration proposals that cannot publish or execute a source change."""

import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from apps.api.schemas.source_config_proposal import (
    SourceConfigProposalCreate,
    SourceConfigProposalDecision,
    SourceConfigProposalResponse,
)
from apps.api.services.pi_runtime import PiRuntimeError, run_pi_proposal
from packages.storage.models.acquisition_mission_run import AcquisitionMissionRun
from packages.storage.models.source_config_proposal import SourceConfigProposal
from packages.storage.models.source_config_version import SourceConfigVersion
from packages.storage.models.source_probe_run import SourceProbeRun

router = APIRouter()


def _unknown(reason: str) -> dict:
    return {
        "proposed_changes": {},
        "unknowns": [reason],
        "expected_effect": "unknown",
        "falsification_condition": "unknown",
        "smallest_verification_action": (
            "Run one bounded probe or mission before proposing a change."
        ),
        "status": "unknown",
    }


def _parse_agent_output(raw: str) -> dict:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return _unknown("Pi output was not a structured configuration proposal.")
    required = {
        "proposed_changes",
        "unknowns",
        "expected_effect",
        "falsification_condition",
        "smallest_verification_action",
    }
    if not isinstance(parsed, dict) or not required.issubset(parsed):
        return _unknown("Pi did not supply all required proposal fields.")
    if not isinstance(parsed["proposed_changes"], dict) or not isinstance(parsed["unknowns"], list):
        return _unknown("Pi proposal fields had an invalid shape.")
    return {**parsed, "status": "proposed"}


@router.post("", response_model=SourceConfigProposalResponse, status_code=201)
async def create_proposal(
    body: SourceConfigProposalCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    config = await db.get(SourceConfigVersion, body.source_config_version_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Source configuration version not found")
    probes = list(
        await db.scalars(select(SourceProbeRun).where(SourceProbeRun.id.in_(body.probe_run_ids)))
    )
    missions = list(
        await db.scalars(
            select(AcquisitionMissionRun).where(AcquisitionMissionRun.id.in_(body.mission_run_ids))
        )
    )
    if len(probes) != len(body.probe_run_ids) or len(missions) != len(body.mission_run_ids):
        raise HTTPException(status_code=422, detail="Every probe and mission artifact must exist")
    if any(probe.source_config_version_id != config.id for probe in probes) or any(
        mission.source_config_version_id != config.id for mission in missions
    ):
        raise HTTPException(
            status_code=422, detail="Artifacts must use the proposed configuration version"
        )
    evidence_refs = [
        {
            "kind": "probe",
            "id": str(probe.id),
            "status": probe.status,
            "detail": probe.outcome_detail,
        }
        for probe in probes
    ] + [
        {
            "kind": "mission",
            "id": str(mission.id),
            "terminal_state": mission.terminal_state,
            "failure_detail": mission.failure_detail,
        }
        for mission in missions
    ]
    if not evidence_refs:
        extracted = _unknown("No probe or mission evidence was supplied.")
        raw_output = {"runtime": "not_called", "reason": extracted["unknowns"][0]}
    else:
        task = (
            "Return JSON only with proposed_changes, unknowns, expected_effect, "
            "falsification_condition, and smallest_verification_action. Propose no budget or "
            "scope expansion. If evidence is insufficient, use empty proposed_changes and unknown."
        )
        try:
            raw_output = await run_pi_proposal(
                run_id=str(uuid.uuid4()),
                task_instruction=task,
                evidence_bundle_hash=str(config.id),
                evidence_bundle=evidence_refs,
                model_version=body.model_version,
                budgets={
                    "max_tool_calls": 0,
                    "max_tokens": body.max_tokens,
                    "max_cost_cents": body.max_cost_cents,
                },
            )
            extracted = _parse_agent_output(str(raw_output.get("raw_output", "")))
        except PiRuntimeError as error:
            extracted = _unknown(f"Pi runtime did not produce a proposal: {error}")
            raw_output = {"runtime": "failed", "error": str(error)}
    proposal = SourceConfigProposal(
        source_config_version_id=config.id,
        evidence_refs=evidence_refs,
        model_version=body.model_version,
        prompt_version=body.prompt_version,
        raw_agent_output=raw_output,
        proposed_changes=extracted["proposed_changes"],
        unknowns=extracted["unknowns"],
        expected_effect=extracted["expected_effect"],
        falsification_condition=extracted["falsification_condition"],
        smallest_verification_action=extracted["smallest_verification_action"],
        status=extracted["status"],
    )
    db.add(proposal)
    await db.commit()
    await db.refresh(proposal)
    return proposal


@router.post("/{proposal_id}/decisions", response_model=SourceConfigProposalResponse)
async def decide_proposal(
    proposal_id: uuid.UUID,
    body: SourceConfigProposalDecision,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    proposal = await db.get(SourceConfigProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Source configuration proposal not found")
    if proposal.status not in {"proposed", "unknown"}:
        raise HTTPException(status_code=409, detail="Proposal was already decided")
    proposal.status = body.decision
    proposal.operator_reason = body.reason
    await db.commit()
    await db.refresh(proposal)
    return proposal
