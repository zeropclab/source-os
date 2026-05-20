"""SourceItem browse and search endpoints."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..dependencies import get_db
from ..schemas.item import SourceItemResponse, SourceItemDetail, SourceItemListResponse
from packages.storage.models.source_item import SourceItem
from packages.storage.models.content_version import ContentVersion
from packages.storage.models.source import Source

router = APIRouter()


@router.get("", response_model=SourceItemListResponse)
async def list_items(
    source_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    min_score: float | None = Query(None),
    q: str | None = Query(None, alias="q"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(SourceItem).options(selectinload(SourceItem.content_versions))
    count_query = select(func.count(SourceItem.id))

    if source_id:
        query = query.where(SourceItem.source_id == source_id)
        count_query = count_query.where(SourceItem.source_id == source_id)
    if status:
        query = query.where(SourceItem.status == status)
        count_query = count_query.where(SourceItem.status == status)

    # PostgreSQL full-text search on related content_versions
    if q:
        query = query.join(ContentVersion, SourceItem.id == ContentVersion.item_id, isouter=True).distinct()
        count_query = count_query.join(
            ContentVersion, SourceItem.id == ContentVersion.item_id, isouter=True
        ).distinct()
        tsquery = func.plainto_tsquery("simple", q)
        query = query.where(ContentVersion.search_vector.op("@@")(tsquery))
        count_query = count_query.where(ContentVersion.search_vector.op("@@")(tsquery))

    # Filter by extraction score
    if min_score is not None:
        query = query.join(ContentVersion, SourceItem.id == ContentVersion.item_id, isouter=True).distinct()
        count_query = count_query.join(
            ContentVersion, SourceItem.id == ContentVersion.item_id, isouter=True
        ).distinct()
        query = query.where(ContentVersion.extraction_score >= min_score)
        count_query = count_query.where(ContentVersion.extraction_score >= min_score)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(SourceItem.discovered_at.desc()).offset(offset).limit(page_size)
    )
    items = result.scalars().all()

    return SourceItemListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{item_id}", response_model=SourceItemDetail)
async def get_item(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    query = (
        select(SourceItem)
        .options(selectinload(SourceItem.content_versions))
        .where(SourceItem.id == item_id)
    )
    result = await db.execute(query)
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Get the latest content version
    versions = sorted(item.content_versions, key=lambda v: v.version_no, reverse=True)
    latest = versions[0] if versions else None

    # Get source info
    source_result = await db.execute(select(Source).where(Source.id == item.source_id))
    source = source_result.scalar_one_or_none()

    return SourceItemDetail(
        id=item.id,
        source_id=item.source_id,
        canonical_url=item.canonical_url,
        platform_item_id=item.platform_item_id,
        title=item.title,
        author=item.author,
        published_at=item.published_at,
        discovered_at=item.discovered_at,
        content_hash=item.content_hash,
        status=item.status,
        content_versions=item.content_versions,
        created_at=item.created_at,
        latest_markdown=latest.markdown if latest else None,
        latest_extraction_score=latest.extraction_score if latest else None,
        source_name=source.name if source else None,
        source_platform=source.platform if source else None,
    )
