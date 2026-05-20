"""Source CRUD endpoints."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db
from ..schemas.source import (
    SourceCreate,
    SourceUpdate,
    SourceResponse,
    SourceListResponse,
)
from packages.storage.models.source import Source

router = APIRouter()


@router.post("", response_model=SourceResponse, status_code=201)
async def create_source(body: SourceCreate, db: AsyncSession = Depends(get_db)):
    source = Source(
        name=body.name,
        platform=body.platform,
        source_type=body.source_type,
        url=body.url,
        monitor_policy=body.monitor_policy.model_dump(),
        fetch_policy=body.fetch_policy.model_dump(),
        compliance_policy=body.compliance_policy.model_dump(),
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.get("", response_model=SourceListResponse)
async def list_sources(
    platform: str | None = Query(None),
    status: str | None = Query("active"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Source)
    count_query = select(func.count(Source.id))

    if platform:
        query = query.where(Source.platform == platform)
        count_query = count_query.where(Source.platform == platform)
    if status:
        query = query.where(Source.status == status)
        count_query = count_query.where(Source.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(query.order_by(Source.created_at.desc()).offset(offset).limit(page_size))
    sources = result.scalars().all()

    return SourceListResponse(items=sources, total=total, page=page, page_size=page_size)


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(source_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.patch("/{source_id}", response_model=SourceResponse)
async def update_source(source_id: uuid.UUID, body: SourceUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if isinstance(value, dict):
            setattr(source, key, value)
        elif value is not None:
            setattr(source, key, value)

    await db.commit()
    await db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=204)
async def delete_source(source_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    await db.delete(source)
    await db.commit()
