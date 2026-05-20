"""Content export endpoints (Markdown, JSONL)."""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from ..dependencies import get_db
from packages.storage.models.source_item import SourceItem
from packages.storage.models.source import Source

router = APIRouter()


class ExportRequest(BaseModel):
    item_ids: list[uuid.UUID]
    format: str = "markdown"  # "markdown" or "jsonl"


@router.post("/items")
async def export_items(body: ExportRequest, db: AsyncSession = Depends(get_db)):
    """Export selected items as Markdown or JSONL."""
    if body.format not in ("markdown", "jsonl"):
        raise HTTPException(status_code=400, detail="Format must be 'markdown' or 'jsonl'")

    query = (
        select(SourceItem)
        .options(selectinload(SourceItem.content_versions))
        .where(SourceItem.id.in_(body.item_ids))
    )
    result = await db.execute(query)
    items = result.scalars().all()

    if not items:
        raise HTTPException(status_code=404, detail="No items found")

    if body.format == "markdown":
        output = _export_markdown(items)
        return PlainTextResponse(content=output, media_type="text/markdown; charset=utf-8")
    else:
        output = _export_jsonl(items)
        return PlainTextResponse(content=output, media_type="application/x-ndjson; charset=utf-8")


def _export_markdown(items) -> str:
    """Render items as Obsidian-compatible markdown with YAML frontmatter."""
    parts = []
    for item in items:
        versions = sorted(item.content_versions, key=lambda v: v.version_no, reverse=True)
        latest = versions[0] if versions else None
        markdown_body = latest.markdown if latest else "*No content extracted*"
        published = item.published_at.strftime("%Y-%m-%d") if item.published_at else ""
        collected = item.discovered_at.strftime("%Y-%m-%d") if item.discovered_at else ""

        parts.append(f"""---
title: "{item.title or 'Untitled'}"
author: "{item.author or ''}"
published: {published}
collected: {collected}
url: {item.canonical_url}
source_item_id: {item.id}
---

{markdown_body}
""")
    return "\n---\n\n".join(parts)


def _export_jsonl(items) -> str:
    """Render items as JSONL."""
    import json

    lines = []
    for item in items:
        versions = sorted(item.content_versions, key=lambda v: v.version_no, reverse=True)
        latest = versions[0] if versions else None
        lines.append(json.dumps({
            "id": str(item.id),
            "source_id": str(item.source_id),
            "title": item.title,
            "author": item.author,
            "url": item.canonical_url,
            "published_at": item.published_at.isoformat() if item.published_at else None,
            "collected_at": item.discovered_at.isoformat() if item.discovered_at else None,
            "markdown": latest.markdown if latest else "",
            "extraction_score": latest.extraction_score if latest else 0.0,
        }, ensure_ascii=False))
    return "\n".join(lines)
