"""First-class internal records for evidence-backed product discovery."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class NeedIssue(Base):
    __tablename__ = "need_issues"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    target_actor: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    problem: Mapped[str] = mapped_column(Text, nullable=False)
    desired_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    workaround: Mapped[str | None] = mapped_column(Text, nullable=True)
    counterevidence_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_validation_action: Mapped[str] = mapped_column(Text, nullable=False)
    unknowns: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    definition_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="captured")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    evidence = relationship(
        "NeedEvidence", back_populates="need_issue", cascade="all, delete-orphan"
    )
    features = relationship(
        "FeatureDefinition", back_populates="need_issue", cascade="all, delete-orphan"
    )
    experiments = relationship(
        "ValidationExperiment", back_populates="need_issue", cascade="all, delete-orphan"
    )
    product_theses = relationship(
        "ProductThesis", back_populates="need_issue", cascade="all, delete-orphan"
    )


class NeedEvidence(Base):
    __tablename__ = "need_evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    need_issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("need_issues.id", ondelete="CASCADE"), nullable=False
    )
    reference_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_uri: Mapped[str] = mapped_column(Text, nullable=False)
    external_signal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("external_signals.id", ondelete="RESTRICT"), nullable=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    need_issue = relationship("NeedIssue", back_populates="evidence")


class NeedIssueVersion(Base):
    __tablename__ = "need_issue_versions"
    __table_args__ = (UniqueConstraint("need_issue_id", "version", name="uq_need_issue_version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    need_issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("need_issues.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    change_reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NeedIssueStatusEvent(Base):
    __tablename__ = "need_issue_status_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    need_issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("need_issues.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[str] = mapped_column(String(32), nullable=False)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NeedChallenge(Base):
    __tablename__ = "need_challenges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    need_issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("need_issues.id", ondelete="CASCADE"), nullable=False
    )
    basis: Mapped[str] = mapped_column(Text, nullable=False)
    unknowns: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    falsification_condition: Mapped[str] = mapped_column(Text, nullable=False)
    smallest_next_action: Mapped[str] = mapped_column(Text, nullable=False)
    assessment: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ValidationExperiment(Base):
    __tablename__ = "validation_experiments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    need_issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("need_issues.id", ondelete="CASCADE"), nullable=False
    )
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    audience: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(Text, nullable=False)
    budget_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    time_limit_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    success_threshold: Mapped[str] = mapped_column(Text, nullable=False)
    negative_threshold: Mapped[str] = mapped_column(Text, nullable=False)
    stop_condition: Mapped[str] = mapped_column(Text, nullable=False)
    requires_external_action: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    wip_override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    approval_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    decision_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    need_issue = relationship("NeedIssue", back_populates="experiments")
    observations = relationship(
        "MarketObservation", back_populates="experiment", cascade="all, delete-orphan"
    )


class MarketObservation(Base):
    __tablename__ = "market_observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("validation_experiments.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    observation: Mapped[str] = mapped_column(Text, nullable=False)
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    experiment = relationship("ValidationExperiment", back_populates="observations")


class ProductThesis(Base):
    __tablename__ = "product_theses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    need_issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("need_issues.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    user: Mapped[str] = mapped_column(Text, nullable=False)
    beneficiary: Mapped[str] = mapped_column(Text, nullable=False)
    decision_maker: Mapped[str] = mapped_column(Text, nullable=False)
    payer: Mapped[str] = mapped_column(Text, nullable=False)
    trigger: Mapped[str] = mapped_column(Text, nullable=False)
    promised_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    alternative: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    delivery_mechanism: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    decision_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    need_issue = relationship("NeedIssue", back_populates="product_theses")
    observations = relationship(
        "ProductThesisObservation", back_populates="product_thesis", cascade="all, delete-orphan"
    )
    build_authorization = relationship(
        "BuildAuthorization",
        back_populates="product_thesis",
        cascade="all, delete-orphan",
        uselist=False,
    )


class ProductThesisObservation(Base):
    __tablename__ = "product_thesis_observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_thesis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_theses.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    observation: Mapped[str] = mapped_column(Text, nullable=False)
    amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    operator_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product_thesis = relationship("ProductThesis", back_populates="observations")


class BuildAuthorization(Base):
    __tablename__ = "build_authorizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_thesis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_theses.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product_thesis = relationship("ProductThesis", back_populates="build_authorization")


class FeatureDefinition(Base):
    __tablename__ = "feature_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    need_issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("need_issues.id", ondelete="CASCADE"), nullable=False
    )
    product_thesis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_theses.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    user_task: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    explicit_exclusions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    acceptance_criteria: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    tracking_events: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    tracking_properties: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    success_metric: Mapped[str] = mapped_column(Text, nullable=False)
    negative_metric: Mapped[str] = mapped_column(Text, nullable=False)
    rollback_condition: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="defined")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    need_issue = relationship("NeedIssue", back_populates="features")
    delivery_records = relationship(
        "DeliveryRecord", back_populates="feature", cascade="all, delete-orphan"
    )


class DeliveryRecord(Base):
    __tablename__ = "delivery_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feature_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("feature_definitions.id", ondelete="CASCADE"), nullable=False
    )
    branch: Mapped[str] = mapped_column(Text, nullable=False)
    implementation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    tests_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk: Mapped[str | None] = mapped_column(Text, nullable=True)
    migration_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    rollback_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    acceptance_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    tracking_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    pr_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in-development")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    feature = relationship("FeatureDefinition", back_populates="delivery_records")
    outcomes = relationship(
        "FeatureOutcome", back_populates="delivery", cascade="all, delete-orphan"
    )


class FeatureOutcome(Base):
    __tablename__ = "feature_outcomes"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("delivery_records.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    observation: Mapped[str] = mapped_column(Text, nullable=False)
    amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    operator_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    delivery = relationship("DeliveryRecord", back_populates="outcomes")


class OutcomeDecision(Base):
    __tablename__ = "outcome_decisions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("delivery_records.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    threshold_comparison: Mapped[str] = mapped_column(Text, nullable=False)
    contribution_margin_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
