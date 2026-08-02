"""Create and retrieve immutable versions of source acquisition configuration."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from apps.api.schemas.source_config_version import (
    SourceConfigVersionCreate,
    SourceConfigVersionResponse,
)
from packages.storage.models.source import Source
from packages.storage.models.source_config_version import SourceConfigVersion

router = APIRouter()


async def _lock_source_or_404(db: AsyncSession, source_id: uuid.UUID) -> None:
    source_exists = await db.scalar(
        select(Source.id).where(Source.id == source_id).with_for_update()
    )
    if source_exists is None:
        raise HTTPException(status_code=404, detail="Source not found")


@router.post(
    "/{source_id}/config-versions",
    response_model=SourceConfigVersionResponse,
    status_code=201,
)
async def create_source_config_version(
    source_id: uuid.UUID,
    body: SourceConfigVersionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _lock_source_or_404(db, source_id)
    latest_version = await db.scalar(
        select(func.max(SourceConfigVersion.version)).where(
            SourceConfigVersion.source_id == source_id
        )
    )
    config = SourceConfigVersion(
        source_id=source_id,
        version=(latest_version or 0) + 1,
        **body.model_dump(),
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.get(
    "/{source_id}/config-versions/{version}",
    response_model=SourceConfigVersionResponse,
)
async def get_source_config_version(
    source_id: uuid.UUID,
    version: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(SourceConfigVersion).where(
            SourceConfigVersion.source_id == source_id,
            SourceConfigVersion.version == version,
        )
    )
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=404, detail="Source configuration version not found")
    return config
