"""Public contracts for immutable source configuration versions."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
NonEmptyTextList = Annotated[list[NonBlankText], Field(min_length=1)]
NonEmptyIntegerList = Annotated[list[int], Field(min_length=1)]
FilterValue = NonBlankText | int | bool | NonEmptyTextList | NonEmptyIntegerList


class QueryScope(BaseModel):
    query_terms: list[NonBlankText] = Field(min_length=1)
    filters: dict[NonBlankText, FilterValue] = Field(default_factory=dict)
    exclusions: list[NonBlankText] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class RequestPolicy(BaseModel):
    request_limit: int = Field(gt=0)
    timeout_seconds: int = Field(gt=0)
    retry_limit: int = Field(default=0, ge=0)

    model_config = ConfigDict(extra="forbid")


class PaginationContextRules(BaseModel):
    page_limit: int = Field(gt=0)
    include_replies: bool = True
    require_parent_context: bool = True

    model_config = ConfigDict(extra="forbid")


class ExtractionSettings(BaseModel):
    parser: NonBlankText
    parser_version: NonBlankText
    content_fields: list[NonBlankText] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class SourceConfigVersionCreate(BaseModel):
    access_mode: Literal[
        "public", "credentialed", "subscription", "rate_limited", "blocked", "unsupported"
    ]
    query_scope: QueryScope
    request_policy: RequestPolicy
    pagination_context_rules: PaginationContextRules
    extraction_settings: ExtractionSettings


class SourceConfigVersionResponse(SourceConfigVersionCreate):
    id: uuid.UUID
    source_id: uuid.UUID
    version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SourceConfigVersionListResponse(BaseModel):
    items: list[SourceConfigVersionResponse]
    total: int
