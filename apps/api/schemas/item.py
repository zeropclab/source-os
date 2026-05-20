"""Pydantic schemas for SourceItem API."""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class ContentVersionBrief(BaseModel):
    id: uuid.UUID
    version_no: int
    extraction_score: float
    created_at: datetime

    model_config = {"from_attributes": True}


class SourceItemResponse(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    canonical_url: str
    platform_item_id: str | None
    title: str | None
    author: str | None
    published_at: datetime | None
    discovered_at: datetime
    content_hash: str | None
    status: str
    content_versions: list[ContentVersionBrief] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class SourceItemDetail(SourceItemResponse):
    latest_markdown: str | None = None
    latest_extraction_score: float | None = None
    source_name: str | None = None
    source_platform: str | None = None


class SourceItemListResponse(BaseModel):
    items: list[SourceItemResponse]
    total: int
    page: int
    page_size: int
