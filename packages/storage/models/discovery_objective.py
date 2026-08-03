"""Durable operator-owned objective and its approved collection boundary."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class DiscoveryObjective(Base):
    """One bounded question the Discovery Agent may investigate."""

    __tablename__ = "discovery_objectives"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    resource_stop_conditions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    evidence_stop_conditions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    decision_stop_conditions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    block_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    boundaries: Mapped[list["ApprovedCollectionBoundary"]] = relationship(
        back_populates="objective",
        cascade="all, delete-orphan",
        order_by="ApprovedCollectionBoundary.version",
        lazy="raise",
    )


class ApprovedCollectionBoundary(Base):
    """An immutable, versioned limit on collection authority for an objective."""

    __tablename__ = "approved_collection_boundaries"
    __table_args__ = (
        UniqueConstraint("objective_id", "version", name="uq_boundary_objective_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    objective_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discovery_objectives.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    approved_source_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    tool_allowlist: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    request_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    time_budget_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_budget_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    credential_scope: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    evidence_conditions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    objective: Mapped[DiscoveryObjective] = relationship(back_populates="boundaries", lazy="raise")


class OperatorApproval(Base):
    """An auditable request to expand or alter collection authority."""

    __tablename__ = "operator_approvals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    objective_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discovery_objectives.id", ondelete="CASCADE"),
        nullable=False,
    )
    request_type: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    requested_boundary_patch: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    operator: Mapped[str | None] = mapped_column(String(120), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class OperatorBoundaryRevision(Base):
    """A material, operator-authored change that creates the next boundary version."""

    __tablename__ = "operator_boundary_revisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    objective_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discovery_objectives.id", ondelete="CASCADE"),
        nullable=False,
    )
    boundary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approved_collection_boundaries.id", ondelete="RESTRICT"),
        nullable=False,
    )
    approval_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operator_approvals.id", ondelete="RESTRICT"),
        nullable=True,
        unique=True,
    )
    operator: Mapped[str] = mapped_column(String(120), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    boundary_patch: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
