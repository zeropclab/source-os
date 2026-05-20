"""Shared domain dataclasses for content interchange between adapters and storage."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Content:
    """Unified content model used throughout the system."""
    url: str
    title: str
    content_type: str  # article, video, podcast, social_post
    source_platform: str
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    collected_at: Optional[datetime] = None
    language: Optional[str] = None
    text_markdown: str = ""
    text_plain: str = ""
    summary: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
