"""Immutable reality signals and their Evidence Inbox triage history."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class ExternalSignal(Base):
    __tablename__ = "external_signals"
    __table_args__ = (UniqueConstraint("lineage_key", name="uq_external_signal_lineage_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mission_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("acquisition_mission_runs.id", ondelete="RESTRICT"),
        nullable=True,
    )
    lineage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_artifact_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_label: Mapped[str] = mapped_column(Text, nullable=False)
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_material: Mapped[str] = mapped_column(Text, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observation: Mapped[str] = mapped_column(Text, nullable=False)
    interpretation: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_context_available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    context_snapshot: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="candidate")
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    triage_events = relationship(
        "SignalTriageEvent",
        back_populates="signal",
        cascade="all, delete-orphan",
        order_by="SignalTriageEvent.created_at",
    )
    mission_run_links = relationship(
        "AcquisitionMissionRunSignal",
        order_by="AcquisitionMissionRunSignal.ordinal",
        lazy="raise",
    )

    @property
    def mission_run_ids(self) -> list[uuid.UUID]:
        return [link.run_id for link in self.mission_run_links]


class SignalTriageEvent(Base):
    __tablename__ = "signal_triage_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    signal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("external_signals.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    signal = relationship("ExternalSignal", back_populates="triage_events")
