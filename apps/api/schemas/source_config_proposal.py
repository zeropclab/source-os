"""Contracts for source-configuration proposals that require an operator decision."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SourceConfigProposalCreate(BaseModel):
    source_config_version_id: uuid.UUID
    probe_run_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    mission_run_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    model_version: str = Field(min_length=1, max_length=100)
    prompt_version: str = Field(min_length=1, max_length=100)
    max_tokens: int = Field(gt=0, le=20_000)
    max_cost_cents: int = Field(ge=0, le=10_000)


class SourceConfigProposalDecision(BaseModel):
    decision: Literal["accepted", "rejected"]
    reason: str = Field(min_length=1, max_length=2_000)


class SourceConfigProposalResponse(BaseModel):
    id: uuid.UUID
    source_config_version_id: uuid.UUID
    evidence_refs: list[dict]
    model_version: str
    prompt_version: str
    raw_agent_output: dict
    proposed_changes: dict
    unknowns: list[str]
    expected_effect: str
    falsification_condition: str
    smallest_verification_action: str
    status: Literal["proposed", "unknown", "accepted", "rejected"]
    operator_reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
