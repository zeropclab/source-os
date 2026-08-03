"""Auditable, bounded cognitive runs that cannot mutate business decisions."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_agent_run_idempotency_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    objective_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discovery_objectives.id", ondelete="RESTRICT"),
        nullable=True,
    )
    boundary_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approved_collection_boundaries.id", ondelete="RESTRICT"),
        nullable=True,
    )
    boundary_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    acquisition_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("acquisition_plans.id", ondelete="RESTRICT"),
        nullable=True,
    )
    input_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    task_instruction: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_bundle: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    evidence_bundle_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    budgets: Mapped[dict] = mapped_column(JSONB, nullable=False)
    tool_allowlist: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    tool_audit: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    usage: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    errors: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    operator_changes: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
