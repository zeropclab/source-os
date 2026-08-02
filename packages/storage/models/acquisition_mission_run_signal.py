"""Durable many-to-many lineage between mission runs and business signals."""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class AcquisitionMissionRunSignal(Base):
    __tablename__ = "acquisition_mission_run_signals"
    __table_args__ = (
        UniqueConstraint("run_id", "ordinal", name="uq_run_signal_ordinal"),
        CheckConstraint("ordinal >= 0", name="ck_run_signal_ordinal_nonnegative"),
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("acquisition_mission_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    signal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("external_signals.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
