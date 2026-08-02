"""Contracts for proposal-only, bounded Agent Runs."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AgentRunCreate(BaseModel):
    evidence_signal_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)
    task_instruction: str = Field(min_length=1, max_length=2_000)
    idempotency_key: str = Field(min_length=1, max_length=255)
    model_version: str = Field(min_length=1, max_length=100)
    prompt_version: str = Field(min_length=1, max_length=100)
    max_tool_calls: int = Field(gt=0, le=20)
    max_tokens: int = Field(gt=0, le=20_000)
    max_cost_cents: int = Field(ge=0, le=10_000)


class AgentRunResponse(BaseModel):
    id: uuid.UUID
    idempotency_key: str
    task_instruction: str
    evidence_bundle: list[dict]
    evidence_bundle_hash: str
    model_version: str
    prompt_version: str
    budgets: dict
    tool_allowlist: list[str]
    tool_audit: list[dict]
    usage: dict
    output: dict | None
    errors: list[dict]
    operator_changes: list[dict]
    status: str
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class AgentRunOperatorDecision(BaseModel):
    decision: str = Field(pattern="^(accepted|modified|rejected)$")
    reason: str = Field(min_length=1, max_length=2_000)
    changes: list[dict] = Field(default_factory=list)
