"""Immutable versioned acquisition configuration for a Source."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class SourceConfigVersion(Base):
    __tablename__ = "source_config_versions"
    __table_args__ = (
        UniqueConstraint("source_id", "version"),
        UniqueConstraint("source_id", "id", name="uq_source_config_source_id_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    access_mode: Mapped[str] = mapped_column(String(24), nullable=False)
    query_scope: Mapped[dict] = mapped_column(JSONB, nullable=False)
    request_policy: Mapped[dict] = mapped_column(JSONB, nullable=False)
    pagination_context_rules: Mapped[dict] = mapped_column(JSONB, nullable=False)
    extraction_settings: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
