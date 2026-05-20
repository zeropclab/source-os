"""Shared API response schemas."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None


class StatsResponse(BaseModel):
    total_sources: int
    active_sources: int
    total_items: int
    total_fetched: int
    success_rate_24h: float
    success_rate_7d: float
    recent_items_per_day: list[dict]
