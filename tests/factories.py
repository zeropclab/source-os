"""Test data factories for SourceOS."""

import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from packages.storage.models.source import Source
from packages.storage.models.source_item import SourceItem
from packages.storage.models.content_version import ContentVersion
from packages.storage.models.fetch_job import FetchJob


async def create_source(
    db: AsyncSession,
    name: str = "Test Source",
    platform: str = "rss",
    source_type: str = "rss_feed",
    url: str = "https://example.com/feed.xml",
    status: str = "active",
    **kwargs,
) -> Source:
    source = Source(
        id=uuid.uuid4(),
        name=name,
        platform=platform,
        source_type=source_type,
        url=url,
        status=status,
        monitor_policy=kwargs.pop("monitor_policy", {}),
        fetch_policy=kwargs.pop("fetch_policy", {}),
        compliance_policy=kwargs.pop("compliance_policy", {}),
        **kwargs,
    )
    db.add(source)
    await db.flush()
    return source


async def create_item(
    db: AsyncSession,
    source_id: uuid.UUID,
    title: str = "Test Item",
    canonical_url: str = "https://example.com/item-1",
    status: str = "discovered",
    **kwargs,
) -> SourceItem:
    item = SourceItem(
        id=uuid.uuid4(),
        source_id=source_id,
        canonical_url=canonical_url,
        title=title,
        status=status,
        discovered_at=kwargs.pop("discovered_at", datetime.now(timezone.utc)),
        **kwargs,
    )
    db.add(item)
    await db.flush()
    return item


async def create_job(
    db: AsyncSession,
    source_id: uuid.UUID | None = None,
    item_id: uuid.UUID | None = None,
    job_type: str = "fetch",
    status: str = "success",
    **kwargs,
) -> FetchJob:
    job = FetchJob(
        id=uuid.uuid4(),
        source_id=source_id,
        item_id=item_id,
        job_type=job_type,
        status=status,
        **kwargs,
    )
    db.add(job)
    await db.flush()
    return job
