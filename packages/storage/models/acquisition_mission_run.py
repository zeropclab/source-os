"""Execution record for one pinned Acquisition Mission."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class AcquisitionMissionRun(Base):
    __tablename__ = "acquisition_mission_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["mission_id", "source_config_version_id"],
            ["acquisition_missions.id", "acquisition_missions.source_config_version_id"],
            name="fk_run_uses_mission_pinned_config",
            ondelete="RESTRICT",
        ),
        CheckConstraint("retry_count >= 0", name="ck_mission_run_retry_count_nonnegative"),
        CheckConstraint(
            "transport_requests >= 0", name="ck_mission_run_transport_requests_nonnegative"
        ),
        CheckConstraint(
            "network_requests >= 0", name="ck_mission_run_network_requests_nonnegative"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_config_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    replay_of_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("acquisition_mission_runs.id", ondelete="RESTRICT"),
        nullable=True,
    )
    execution_mode: Mapped[str] = mapped_column(String(24), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="completed", server_default="completed"
    )
    control_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_attempt: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    lease_owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    input_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    budgets: Mapped[dict] = mapped_column(JSONB, nullable=False)
    raw_artifacts: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    parser_version: Mapped[str] = mapped_column(String(100), nullable=False)
    context_completeness: Mapped[dict] = mapped_column(JSONB, nullable=False)
    checkpoints: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False)
    terminal_state: Mapped[str] = mapped_column(String(24), nullable=False)
    failure_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    transport_requests: Mapped[int] = mapped_column(Integer, nullable=False)
    network_requests: Mapped[int] = mapped_column(Integer, nullable=False)
    external_signal_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
