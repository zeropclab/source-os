"""Proposal-only revisions of immutable source configuration versions."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class SourceConfigProposal(Base):
    __tablename__ = "source_config_proposals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_config_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_config_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    evidence_refs: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_agent_output: Mapped[dict] = mapped_column(JSONB, nullable=False)
    proposed_changes: Mapped[dict] = mapped_column(JSONB, nullable=False)
    unknowns: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    expected_effect: Mapped[str] = mapped_column(Text, nullable=False)
    falsification_condition: Mapped[str] = mapped_column(Text, nullable=False)
    smallest_verification_action: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    operator_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
