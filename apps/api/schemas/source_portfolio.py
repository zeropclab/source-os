"""Schemas for recorded source portfolio assessments."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SourcePortfolioAssessmentCreate(BaseModel):
    source_id: uuid.UUID
    region: str = Field(min_length=1, max_length=100)
    language: str = Field(min_length=1, max_length=32)
    audience: str = Field(min_length=1, max_length=128)
    evidence_type: str = Field(min_length=1, max_length=128)
    portfolio_mode: Literal["exploration", "exploitation"]
    technical_success_rate: float = Field(ge=0, le=1)
    context_completeness_rate: float = Field(ge=0, le=1)
    evidence_usefulness_rate: float = Field(ge=0, le=1)
    independent_evidence_count: int = Field(ge=0)
    counterevidence_count: int = Field(ge=0)
    estimated_cost_cents: int = Field(ge=0)
    downstream_decision_impact: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class SourcePortfolioAssessmentResponse(SourcePortfolioAssessmentCreate):
    id: uuid.UUID
    recommended_action: Literal["add", "reduce", "pause", "counter_sample"]
    created_at: datetime

    model_config = {"from_attributes": True}
