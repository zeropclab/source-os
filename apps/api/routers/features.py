"""Browse defined Features without detaching them from their delivery evidence."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from apps.api.schemas.need_issue import FeatureDefinitionListResponse
from packages.storage.models.need_issue import FeatureDefinition

router = APIRouter()


@router.get("", response_model=FeatureDefinitionListResponse)
async def list_feature_definitions(
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(FeatureDefinition)
    count_query = select(func.count(FeatureDefinition.id))
    if status is not None:
        query = query.where(FeatureDefinition.status == status)
        count_query = count_query.where(FeatureDefinition.status == status)
    total = await db.scalar(count_query) or 0
    features = await db.scalars(
        query.order_by(FeatureDefinition.updated_at.desc(), FeatureDefinition.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return FeatureDefinitionListResponse(
        items=list(features), total=total, page=page, page_size=page_size
    )
