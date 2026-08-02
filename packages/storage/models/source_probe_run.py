"""Persisted outcomes of bounded probes against immutable source configurations."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class SourceProbeRun(Base):
    __tablename__ = "source_probe_runs"

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
    sample: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    pagination_supported: Mapped[bool] = mapped_column(Boolean, nullable=False)
    replies_supported: Mapped[bool] = mapped_column(Boolean, nullable=False)
    context_risks: Mapped[list] = mapped_column(JSONB, nullable=False)
    consumed_requests: Mapped[int] = mapped_column(Integer, nullable=False)
    elapsed_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
