"""Public contracts for bounded Discovery Objectives."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class InitialCollectionBoundary(BaseModel):
    approved_source_ids: list[uuid.UUID] = Field(min_length=1)
    tool_allowlist: list[NonEmptyText] = Field(min_length=1)
    request_limit: int = Field(gt=0)
    time_budget_minutes: int = Field(gt=0)
    cost_budget_cents: int = Field(ge=0)


class DiscoveryObjectiveCreate(BaseModel):
    title: NonEmptyText = Field(max_length=200)
    question: NonEmptyText
    resource_stop_conditions: list[NonEmptyText] = Field(min_length=1)
    evidence_stop_conditions: list[NonEmptyText] = Field(min_length=1)
    decision_stop_conditions: list[NonEmptyText] = Field(min_length=1)
    initial_boundary: InitialCollectionBoundary


class ApprovedCollectionBoundaryResponse(BaseModel):
    id: uuid.UUID
    objective_id: uuid.UUID
    version: int
    approved_source_ids: list[uuid.UUID]
    tool_allowlist: list[str]
    request_limit: int
    time_budget_minutes: int
    cost_budget_cents: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DiscoveryObjectiveResponse(BaseModel):
    id: uuid.UUID
    title: str
    question: str
    resource_stop_conditions: list[str]
    evidence_stop_conditions: list[str]
    decision_stop_conditions: list[str]
    status: str
    created_at: datetime
    updated_at: datetime
    current_boundary: ApprovedCollectionBoundaryResponse

    model_config = {"from_attributes": True}


class DiscoveryObjectiveWorkspaceResponse(BaseModel):
    objective: DiscoveryObjectiveResponse
    current_boundary: ApprovedCollectionBoundaryResponse
    plans: list[object] = Field(default_factory=list)
    assessments: list[object] = Field(default_factory=list)
