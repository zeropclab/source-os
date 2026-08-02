"""Public contracts for bounded Acquisition Mission drafts."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from apps.api.schemas.source_config_version import SourceConfigVersionResponse

StopCondition = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AcquisitionMissionFields(BaseModel):
    reality_question: str = Field(min_length=1)
    mission_type: Literal["exploratory", "targeted_evidence", "counterevidence", "context_repair"]
    source_id: uuid.UUID
    regions: list[str] = Field(min_length=1)
    languages: list[str] = Field(min_length=1)
    target_audience: str = Field(min_length=1)
    query_seeds: list[str] = Field(min_length=1)
    time_budget_minutes: int = Field(gt=0)
    item_limit: int = Field(gt=0)
    cost_budget_cents: int = Field(ge=0)
    stop_conditions: list[StopCondition] = Field(min_length=1)


class AcquisitionMissionCreate(AcquisitionMissionFields):
    source_config_version_id: uuid.UUID


class AcquisitionMissionResponse(AcquisitionMissionFields):
    id: uuid.UUID
    source_config_version_id: uuid.UUID | None
    source_config_version: SourceConfigVersionResponse | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AcquisitionMissionListResponse(BaseModel):
    items: list[AcquisitionMissionResponse]
    total: int
    page: int
    page_size: int
