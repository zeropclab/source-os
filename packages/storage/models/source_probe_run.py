"""Persisted outcomes of bounded probes against immutable source configurations."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class SourceProbeRun(Base):
    __tablename__ = "source_probe_runs"
    __table_args__ = (
        CheckConstraint("request_budget > 0", name="ck_probe_request_budget_positive"),
        CheckConstraint("time_budget_seconds > 0", name="ck_probe_time_budget_positive"),
        CheckConstraint("consumed_requests >= 0", name="ck_probe_consumed_requests_nonnegative"),
        CheckConstraint(
            "consumed_requests <= request_budget", name="ck_probe_consumed_within_budget"
        ),
        CheckConstraint("elapsed_ms >= 0", name="ck_probe_elapsed_nonnegative"),
        CheckConstraint("status IN ('succeeded', 'empty', 'failed')", name="ck_probe_status_valid"),
        CheckConstraint(
            "access_state IN ('public', 'credentialed', 'subscription', 'rate_limited', "
            "'blocked', 'unsupported')",
            name="ck_probe_access_state_valid",
        ),
        CheckConstraint(
            "sample_available = (sample IS NOT NULL)", name="ck_probe_sample_flag_consistent"
        ),
        CheckConstraint(
            "status <> 'succeeded' OR sample_available", name="ck_probe_success_has_sample"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_config_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_config_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    request_budget: Mapped[int] = mapped_column(Integer, nullable=False)
    time_budget_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    access_state: Mapped[str] = mapped_column(String(24), nullable=False)
    sample_available: Mapped[bool] = mapped_column(Boolean, nullable=False)
    sample: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    pagination_supported: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    replies_supported: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    context_risks: Mapped[list] = mapped_column(JSONB, nullable=False)
    consumed_requests: Mapped[int] = mapped_column(Integer, nullable=False)
    elapsed_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
