"""Pydantic schemas for Source API."""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class MonitorPolicy(BaseModel):
    frequency: str = "2h"
    method: str = "rss_poll"
    list_selector: str | None = None
    date_selector: str | None = None
    dedup_key: str = "canonical_url"


class FetchPolicy(BaseModel):
    preferred_strategy: str = "http"
    fallback_strategy: str | None = "browser"
    extractors: list[str] = Field(default_factory=lambda: ["trafilatura"])
    download_media: bool = False


class CompliancePolicy(BaseModel):
    respect_robots: bool = True
    max_requests_per_hour: int = 20
    require_auth: bool = False
    media_download_allowed: bool = True


class SourceCreate(BaseModel):
    name: str = Field(..., max_length=255)
    platform: str
    source_type: str
    url: str
    monitor_policy: MonitorPolicy = Field(default_factory=MonitorPolicy)
    fetch_policy: FetchPolicy = Field(default_factory=FetchPolicy)
    compliance_policy: CompliancePolicy = Field(default_factory=CompliancePolicy)


class SourceUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    url: str | None = None
    status: str | None = None
    monitor_policy: MonitorPolicy | None = None
    fetch_policy: FetchPolicy | None = None
    compliance_policy: CompliancePolicy | None = None


class SourceResponse(BaseModel):
    id: uuid.UUID
    name: str
    platform: str
    source_type: str
    url: str
    monitor_policy: dict
    fetch_policy: dict
    compliance_policy: dict
    status: str
    last_checked_at: datetime | None
    next_check_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SourceListResponse(BaseModel):
    items: list[SourceResponse]
    total: int
    page: int
    page_size: int
