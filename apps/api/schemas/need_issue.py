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
    next_validation_action: str = Field(min_length=1)


class NeedIssueTransition(BaseModel):
    status: NeedStatus


class NeedEvidenceCreate(BaseModel):
    reference_type: str = Field(min_length=1, max_length=32)
    reference_uri: str = Field(min_length=1)
    role: Literal["supporting", "counter"]
    excerpt: str | None = None


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
    next_validation_action: str
    status: str
    evidence_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
