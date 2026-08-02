"""First-class internal records for evidence-backed product discovery."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
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


class NeedEvidence(Base):
    __tablename__ = "need_evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    need_issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("need_issues.id", ondelete="CASCADE"), nullable=False
    )
    reference_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_uri: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    need_issue = relationship("NeedIssue", back_populates="evidence")


class FeatureDefinition(Base):
    __tablename__ = "feature_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    need_issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("need_issues.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    user_task: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    acceptance_criteria: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    tracking_events: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    tracking_properties: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    success_metric: Mapped[str] = mapped_column(Text, nullable=False)
    negative_metric: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="defined")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    need_issue = relationship("NeedIssue", back_populates="features")
