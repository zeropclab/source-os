"""DiscoveredItem dataclass — represents a new item found during monitoring."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class DiscoveredItem:
    """Represents a new item found during source monitoring."""
    platform_item_id: str          # Platform native ID (video_id, RSS GUID, etc.)
    canonical_url: str             # Normalized URL for deduplication
    title: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)
