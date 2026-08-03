"""Versioned collection plans owned by Discovery Objectives."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .acquisition_mission import AcquisitionMission


class AcquisitionPlan(Base):
    __tablename__ = "acquisition_plans"
    __table_args__ = (
        UniqueConstraint("objective_id", "version", name="uq_plan_objective_version"),
    )

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
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    selected_source_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    counterevidence_target: Mapped[str] = mapped_column(Text, nullable=False)
    request_budget: Mapped[int] = mapped_column(Integer, nullable=False)
    time_budget_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_budget_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    missions: Mapped[list["AcquisitionMission"]] = relationship(
        back_populates="acquisition_plan", lazy="raise"
    )


class PlanRevision(Base):
    __tablename__ = "plan_revisions"
    __table_args__ = (UniqueConstraint("plan_id", name="uq_plan_revision_plan"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("acquisition_plans.id", ondelete="CASCADE"), nullable=False
    )
    predecessor_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("acquisition_plans.id", ondelete="RESTRICT"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    delta: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    plan: Mapped[AcquisitionPlan] = relationship(
        foreign_keys=[plan_id], lazy="raise", uselist=False
    )
