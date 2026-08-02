"""Pydantic schemas for the Need Issue workflow."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

NeedStatus = Literal[
    "captured",
    "triaged",
    "evidence-backed",
    "discovery-validated",
    "feature-defined",
    "in-development",
    "review-ready",
    "merged",
    "released",
    "measured",
    "retained",
    "dormant",
    "rejected",
]


class NeedIssueCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    target_actor: str = Field(min_length=1)
    context: str = Field(min_length=1)
    problem: str = Field(min_length=1)
    desired_outcome: str = Field(min_length=1)
    workaround: str | None = None
    counterevidence_summary: str | None = None
    unknowns: list[str] = Field(default_factory=list)
    next_validation_action: str = Field(min_length=1)


class NeedEvidenceCreate(BaseModel):
    reference_type: str = Field(min_length=1, max_length=32)
    reference_uri: str = Field(min_length=1)
    external_signal_id: uuid.UUID | None = None
    role: Literal["supporting", "counter"]
    excerpt: str | None = None


class NeedIssueTransition(BaseModel):
    status: NeedStatus
    reason: str | None = Field(default=None, min_length=1)
    new_evidence: NeedEvidenceCreate | None = None


class NeedIssueUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    target_actor: str | None = Field(default=None, min_length=1)
    context: str | None = Field(default=None, min_length=1)
    problem: str | None = Field(default=None, min_length=1)
    desired_outcome: str | None = Field(default=None, min_length=1)
    workaround: str | None = None
    counterevidence_summary: str | None = None
    unknowns: list[str] | None = None
    next_validation_action: str | None = Field(default=None, min_length=1)
    change_reason: str = Field(min_length=1)


class NeedEvidenceResponse(NeedEvidenceCreate):
    id: uuid.UUID
    need_issue_id: uuid.UUID
    captured_at: datetime

    model_config = {"from_attributes": True}


class FeatureDefinitionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    user_task: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    acceptance_criteria: list[str] = Field(min_length=1)
    tracking_events: list[str] = Field(min_length=1)
    tracking_properties: list[str] = Field(min_length=1)
    success_metric: str = Field(min_length=1)
    negative_metric: str = Field(min_length=1)


class FeatureDefinitionResponse(FeatureDefinitionCreate):
    id: uuid.UUID
    need_issue_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NeedIssueResponse(BaseModel):
    id: uuid.UUID
    title: str
    target_actor: str
    context: str
    problem: str
    desired_outcome: str
    workaround: str | None
    counterevidence_summary: str | None
    unknowns: list[str]
    next_validation_action: str
    status: str
    definition_version: int
    evidence_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
