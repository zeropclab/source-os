"""Pydantic schemas for immutable reality signals and Evidence Inbox triage."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ExternalSignalCreate(BaseModel):
    source_label: str = Field(min_length=1)
    source_uri: str | None = None
    original_material: str = Field(min_length=1)
    observed_at: datetime
    observation: str = Field(min_length=1)
    interpretation: str | None = None


class SignalTriageCreate(BaseModel):
    status: Literal["accepted", "ignored", "flagged"]
    reason: str = Field(min_length=1)


class SignalTriageEventResponse(BaseModel):
    id: uuid.UUID
    status: str
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ExternalSignalResponse(BaseModel):
    id: uuid.UUID
    source_label: str
    source_uri: str | None
    original_material: str
    observed_at: datetime
    observation: str
    interpretation: str | None
    status: str
    captured_at: datetime
    triage_events: list[SignalTriageEventResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class EvidenceInboxResponse(BaseModel):
    items: list[ExternalSignalResponse]
