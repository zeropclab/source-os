"""Pydantic schemas for FetchJob API."""

import uuid
from datetime import datetime
from pydantic import BaseModel


class FetchJobResponse(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID | None
    item_id: uuid.UUID | None
    job_type: str
    status: str
    rq_job_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    retry_count: int
    error_code: str | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FetchJobListResponse(BaseModel):
    items: list[FetchJobResponse]
    total: int
    page: int
    page_size: int


class RetryResponse(BaseModel):
    message: str
    new_job_id: str | None = None
