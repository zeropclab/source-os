"""Auditable source-quality assessments; these are not market-representativeness claims."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class SourcePortfolioAssessment(Base):
    __tablename__ = "source_portfolio_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    audience: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(128), nullable=False)
    portfolio_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    technical_success_rate: Mapped[float] = mapped_column(nullable=False)
    context_completeness_rate: Mapped[float] = mapped_column(nullable=False)
    evidence_usefulness_rate: Mapped[float] = mapped_column(nullable=False)
    independent_evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    counterevidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_cost_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    downstream_decision_impact: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
