"""Evidence-cited judgements and operator-promotable Need Hypotheses."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class DiscoveryAssessment(Base):
    __tablename__ = "discovery_assessments"
    __table_args__ = (
        UniqueConstraint("objective_id", "version", name="uq_assessment_objective_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    objective_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discovery_objectives.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    assessment_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    unknowns: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    coverage_gaps: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class NeedHypothesis(Base):
    __tablename__ = "need_hypotheses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    objective_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discovery_objectives.id", ondelete="CASCADE"),
        nullable=False,
    )
    support_assessment_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    target_actor: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    problem: Mapped[str] = mapped_column(Text, nullable=False)
    desired_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    workaround: Mapped[str | None] = mapped_column(Text, nullable=True)
    unknowns: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    next_validation_action: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    promoted_need_issue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("need_issues.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
