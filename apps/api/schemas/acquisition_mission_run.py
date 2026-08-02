"""Public contracts for Acquisition Mission executions."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AcquisitionMissionRunCreate(BaseModel):
    execution_mode: Literal["fixture", "live"]

    model_config = {"extra": "forbid"}


class AcquisitionMissionDryRunCreate(BaseModel):
    """A deliberately smaller preview of a pinned mission, before evidence is persisted."""

    execution_mode: Literal["fixture", "live"]
    preview_item_limit: int = Field(gt=0)
    preview_request_limit: int = Field(gt=0)

    model_config = {"extra": "forbid"}


class AcquisitionMissionRunResponse(BaseModel):
    id: uuid.UUID
    mission_id: uuid.UUID
    source_config_version_id: uuid.UUID
    replay_of_run_id: uuid.UUID | None
    execution_mode: str
    input_snapshot: dict
    budgets: dict
    raw_artifacts: list[dict]
    parser_version: str
    context_completeness: dict
    checkpoints: list[str]
    retry_count: int
    terminal_state: str
    failure_detail: str | None
    transport_requests: int
    network_requests: int
    external_signal_ids: list[uuid.UUID]
    started_at: datetime
    completed_at: datetime

    model_config = {"from_attributes": True}
