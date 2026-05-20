"""FetchResult dataclass — represents the result of fetching and extracting a single item."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class FetchResult:
    """Result of fetching and extracting content from a single URL."""
    title: str
    extracted_markdown: str
    extracted_text: str
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)
    extraction_score: float = 0.0
    media_urls: list[str] = field(default_factory=list)
    raw_html: Optional[str] = None
