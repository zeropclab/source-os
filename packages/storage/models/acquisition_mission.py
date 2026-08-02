"""A bounded intent for collecting evidence about one reality question."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class AcquisitionMission(Base):
    __tablename__ = "acquisition_missions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    reality_question: Mapped[str] = mapped_column(Text, nullable=False)
    mission_type: Mapped[str] = mapped_column(String(32), nullable=False)
    regions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    languages: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    target_audience: Mapped[str] = mapped_column(Text, nullable=False)
    query_seeds: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    time_budget_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    item_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_budget_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    stop_conditions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
