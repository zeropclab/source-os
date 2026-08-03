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
    credential_scope: list[NonEmptyText] = Field(default_factory=list)
    evidence_conditions: list[NonEmptyText] = Field(default_factory=list)


class BoundaryPatch(BaseModel):
    approved_source_ids: list[uuid.UUID] | None = Field(default=None, min_length=1)
    tool_allowlist: list[NonEmptyText] | None = Field(default=None, min_length=1)
    request_limit: int | None = Field(default=None, gt=0)
    time_budget_minutes: int | None = Field(default=None, gt=0)
    cost_budget_cents: int | None = Field(default=None, ge=0)
    credential_scope: list[NonEmptyText] | None = None
    evidence_conditions: list[NonEmptyText] | None = None


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
    credential_scope: list[str]
    evidence_conditions: list[str]
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
    plans: list["AcquisitionPlanResponse"] = Field(default_factory=list)
    assessments: list["DiscoveryAssessmentResponse"] = Field(default_factory=list)
    pending_approvals: list["OperatorApprovalResponse"] = Field(default_factory=list)
    boundary_revisions: list["OperatorBoundaryRevisionResponse"] = Field(default_factory=list)


class OperatorApprovalCreate(BaseModel):
    request_type: NonEmptyText = Field(max_length=64)
    reason: NonEmptyText
    requested_boundary_patch: BoundaryPatch


class OperatorApprovalDecision(BaseModel):
    operator: NonEmptyText = Field(max_length=120)
    reason: NonEmptyText


class OperatorApprovalResponse(BaseModel):
    id: uuid.UUID
    objective_id: uuid.UUID
    request_type: str
    reason: str
    requested_boundary_patch: dict
    status: str
    operator: str | None
    decision_reason: str | None
    decided_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OperatorBoundaryRevisionCreate(BaseModel):
    operator: NonEmptyText = Field(max_length=120)
    reason: NonEmptyText
    boundary_patch: BoundaryPatch


class OperatorBoundaryRevisionResponse(BaseModel):
    id: uuid.UUID
    objective_id: uuid.UUID
    boundary_id: uuid.UUID
    boundary_version: int
    approval_id: uuid.UUID | None
    operator: str
    reason: str
    boundary_patch: dict
    created_at: datetime


class ObjectiveBlockRequest(BaseModel):
    reason: NonEmptyText


class AcquisitionPlanCreate(BaseModel):
    question: NonEmptyText
    selected_source_ids: list[uuid.UUID] = Field(min_length=1)
    counterevidence_target: NonEmptyText
    request_budget: int = Field(gt=0)
    time_budget_minutes: int = Field(gt=0)
    cost_budget_cents: int = Field(ge=0)
    predecessor_plan_id: uuid.UUID | None = None
    revision_reason: NonEmptyText | None = None
    revision_delta: dict | None = None


class PlanRevisionResponse(BaseModel):
    id: uuid.UUID
    predecessor_plan_id: uuid.UUID
    reason: str
    delta: dict
    created_at: datetime


class AcquisitionPlanResponse(BaseModel):
    id: uuid.UUID
    objective_id: uuid.UUID
    boundary_id: uuid.UUID
    boundary_version: int
    version: int
    question: str
    selected_source_ids: list[uuid.UUID]
    counterevidence_target: str
    request_budget: int
    time_budget_minutes: int
    cost_budget_cents: int
    created_at: datetime
    predecessor_plan_id: uuid.UUID | None
    revision: PlanRevisionResponse | None
    missions: list[uuid.UUID]


class DiscoveryAssessmentCreate(BaseModel):
    kind: str = Field(
        pattern="^(support|counterevidence|unknown|coverage_gap|blocked|recommendation)$"
    )
    statement: NonEmptyText
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    assessment_ids: list[uuid.UUID] = Field(default_factory=list)
    unknowns: list[NonEmptyText] = Field(default_factory=list)
    coverage_gaps: list[NonEmptyText] = Field(default_factory=list)
    recommendation: NonEmptyText | None = None


class DiscoveryAssessmentResponse(DiscoveryAssessmentCreate):
    id: uuid.UUID
    objective_id: uuid.UUID
    version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class NeedHypothesisCreate(BaseModel):
    title: NonEmptyText = Field(max_length=255)
    target_actor: NonEmptyText
    context: NonEmptyText
    problem: NonEmptyText
    desired_outcome: NonEmptyText
    workaround: NonEmptyText | None = None
    unknowns: list[NonEmptyText] = Field(default_factory=list)
    next_validation_action: NonEmptyText
    support_assessment_ids: list[uuid.UUID] = Field(min_length=1)


class NeedHypothesisResponse(NeedHypothesisCreate):
    id: uuid.UUID
    objective_id: uuid.UUID
    status: str
    promoted_need_issue_id: uuid.UUID | None
    created_at: datetime
    model_config = {"from_attributes": True}


class NeedHypothesisPromotion(BaseModel):
    operator: NonEmptyText
