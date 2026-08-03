import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class DiscoveryDecisionRecord(Base):
    __tablename__ = "discovery_decision_records"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    objective_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discovery_objectives.id", ondelete="RESTRICT"), unique=True
    )
    decision: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(Text)
    support_assessment_ids: Mapped[list[str]] = mapped_column(JSONB)
    counter_assessment_ids: Mapped[list[str]] = mapped_column(JSONB)
    unknowns: Mapped[list[str]] = mapped_column(JSONB)
    resource_usage: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OutcomeFeedback(Base):
    __tablename__ = "outcome_feedback"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discovery_decision_records.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(32))
    reference: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
