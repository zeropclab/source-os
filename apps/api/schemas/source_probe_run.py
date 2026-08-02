"""Public contracts for bounded source probe runs."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SourceProbeRunCreate(BaseModel):
    request_budget: int = Field(gt=0)
    time_budget_seconds: int = Field(gt=0)

    model_config = {"extra": "forbid"}


class SourceProbeRunResponse(SourceProbeRunCreate):
    id: uuid.UUID
    source_config_version_id: uuid.UUID
    status: Literal["succeeded", "empty", "failed"]
    access_state: Literal[
        "public", "credentialed", "subscription", "rate_limited", "blocked", "unsupported"
    ]
    sample_available: bool
    sample: dict[str, str] | None
    pagination_supported: bool | None
    replies_supported: bool | None
    context_risks: list[str]
    consumed_requests: int
    elapsed_ms: int
    outcome_detail: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
