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


class NeedIssueFromAcceptedSignalCreate(NeedIssueCreate):
    external_signal_id: uuid.UUID
    excerpt: str | None = None


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
    override_gate: bool = False


class NeedChallengeCreate(BaseModel):
    basis: str = Field(min_length=1)
    unknowns: list[str] = Field(min_length=1)
    falsification_condition: str = Field(min_length=1)
    smallest_next_action: str = Field(min_length=1)
    assessment: Literal[
        "temporarily-supported", "falsified", "insufficient-evidence", "genuine-disagreement"
    ]


class NeedChallengeResponse(NeedChallengeCreate):
    id: uuid.UUID
    need_issue_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class OntologyHypothesisCreate(BaseModel):
    relationship_path: list[str] = Field(min_length=2)
    source_material: str = Field(min_length=1)
    counterexample: str = Field(min_length=1)
    unknowns: list[str] = Field(min_length=1)
    smallest_validation_action: str = Field(min_length=1)


class OntologyHypothesisResponse(OntologyHypothesisCreate):
    id: uuid.UUID
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}


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
    product_thesis_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    user_task: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    explicit_exclusions: list[str] = Field(min_length=1)
    acceptance_criteria: list[str] = Field(min_length=1)
    tracking_events: list[str] = Field(min_length=1)
    tracking_properties: list[str] = Field(min_length=1)
    success_metric: str = Field(min_length=1)
    negative_metric: str = Field(min_length=1)
    rollback_condition: str = Field(min_length=1)


class FeatureDefinitionResponse(FeatureDefinitionCreate):
    id: uuid.UUID
    need_issue_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FeatureDefinitionListResponse(BaseModel):
    items: list[FeatureDefinitionResponse]
    total: int
    page: int
    page_size: int


class BuildAuthorizationCreate(BaseModel):
    rationale: str = Field(min_length=1)


class BuildAuthorizationResponse(BuildAuthorizationCreate):
    id: uuid.UUID
    product_thesis_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class DeliveryRecordCreate(BaseModel):
    branch: str = Field(min_length=1)
    implementation_version: str = Field(min_length=1, max_length=64)
    tests_evidence: str | None = None
    review_conclusion: str | None = None
    risk: str | None = None
    migration_evidence: str | None = None
    rollback_evidence: str | None = None
    acceptance_evidence: str | None = None
    tracking_evidence: str | None = None
    pr_reference: str | None = None


class DeliveryRecordResponse(DeliveryRecordCreate):
    id: uuid.UUID
    feature_definition_id: uuid.UUID
    status: str
    created_at: datetime
    released_at: datetime | None

    model_config = {"from_attributes": True}


class FeatureOutcomeCreate(BaseModel):
    kind: Literal["activation", "repeated_use", "payment", "refund", "churn", "support", "cost"]
    properties: dict = Field(default_factory=dict)
    observation: str = Field(min_length=1)
    amount_cents: int | None = None
    operator_minutes: int | None = Field(default=None, ge=0)
    cost_category: str | None = None


class FeatureOutcomeResponse(FeatureOutcomeCreate):
    id: uuid.UUID
    delivery_record_id: uuid.UUID
    created_at: datetime
    model_config = {"from_attributes": True}


class OutcomeDecisionCreate(BaseModel):
    decision: Literal["retain", "iterate", "rollback", "stop"]
    threshold_comparison: str = Field(min_length=1)
    contribution_margin_cents: int
    rationale: str = Field(min_length=1)


class OutcomeDecisionResponse(OutcomeDecisionCreate):
    id: uuid.UUID
    delivery_record_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class DeliveryRecordWorkbenchResponse(DeliveryRecordResponse):
    outcomes: list[FeatureOutcomeResponse]
    outcome_decision: OutcomeDecisionResponse | None


class FeatureDeliveryWorkbenchResponse(BaseModel):
    feature_definition: FeatureDefinitionResponse
    deliveries: list[DeliveryRecordWorkbenchResponse]
    gaps: list[str]


class ValidationExperimentCreate(BaseModel):
    hypothesis: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    method: str = Field(min_length=1)
    budget_cents: int = Field(ge=0)
    time_limit_hours: int = Field(gt=0)
    success_threshold: str = Field(min_length=1)
    negative_threshold: str = Field(min_length=1)
    stop_condition: str = Field(min_length=1)
    requires_external_action: bool = True
    wip_override_reason: str | None = Field(default=None, min_length=1)


class ValidationExperimentResponse(ValidationExperimentCreate):
    id: uuid.UUID
    need_issue_id: uuid.UUID
    status: str
    approval_note: str | None
    decision: str | None
    decision_rationale: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExperimentApproval(BaseModel):
    operator_note: str = Field(min_length=1)


class MarketObservationCreate(BaseModel):
    kind: Literal["response", "refusal", "silence", "trial", "payment", "refund", "cost"]
    observation: str = Field(min_length=1)
    source_uri: str | None = None
    amount_cents: int | None = Field(default=None, ge=0)


class MarketObservationResponse(MarketObservationCreate):
    id: uuid.UUID
    experiment_id: uuid.UUID
    observed_at: datetime

    model_config = {"from_attributes": True}


class ExperimentDecision(BaseModel):
    decision: Literal["continue", "change", "stop"]
    rationale: str = Field(min_length=1)


class ProductThesisCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    user: str = Field(min_length=1)
    beneficiary: str = Field(min_length=1)
    decision_maker: str = Field(min_length=1)
    payer: str = Field(min_length=1)
    trigger: str = Field(min_length=1)
    promised_outcome: str = Field(min_length=1)
    alternative: str = Field(min_length=1)
    channel: str = Field(min_length=1)
    price_cents: int = Field(ge=0)
    delivery_mechanism: str = Field(min_length=1)
    delivery_mode: Literal["manual", "service-assisted", "automated"]


class ProductThesisResponse(ProductThesisCreate):
    id: uuid.UUID
    need_issue_id: uuid.UUID
    status: str
    decision: str | None
    decision_rationale: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductThesisListResponse(BaseModel):
    items: list[ProductThesisResponse]
    total: int
    page: int
    page_size: int


class ProductThesisObservationCreate(BaseModel):
    kind: Literal["quote", "purchase", "refusal", "refund", "delivery_effort", "direct_cost"]
    observation: str = Field(min_length=1)
    amount_cents: int | None = Field(default=None, ge=0)
    operator_minutes: int | None = Field(default=None, ge=0)


class ProductThesisObservationResponse(ProductThesisObservationCreate):
    id: uuid.UUID
    product_thesis_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductThesisDecision(BaseModel):
    decision: Literal["continue", "change", "stop"]
    rationale: str = Field(min_length=1)


class ProductThesisWorkbenchResponse(BaseModel):
    product_thesis: ProductThesisResponse
    observations: list[ProductThesisObservationResponse]
    build_authorization: BuildAuthorizationResponse | None
    gaps: list[str]


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


class NeedIssueListResponse(BaseModel):
    items: list[NeedIssueResponse]
    total: int
    page: int
    page_size: int
