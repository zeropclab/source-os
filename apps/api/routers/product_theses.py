"""Product Thesis offers and their observable economic evidence."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from apps.api.schemas.need_issue import (
    BuildAuthorizationCreate,
    BuildAuthorizationResponse,
    ProductThesisDecision,
    ProductThesisListResponse,
    ProductThesisObservationCreate,
    ProductThesisObservationResponse,
    ProductThesisResponse,
    ProductThesisWorkbenchResponse,
)
from packages.storage.models.need_issue import (
    BuildAuthorization,
    ProductThesis,
    ProductThesisObservation,
)

router = APIRouter()


async def _thesis_or_404(db: AsyncSession, thesis_id: uuid.UUID) -> ProductThesis:
    thesis = await db.get(ProductThesis, thesis_id)
    if thesis is None:
        raise HTTPException(status_code=404, detail="Product Thesis not found")
    return thesis


@router.get("", response_model=ProductThesisListResponse)
async def list_product_theses(
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(ProductThesis)
    count_query = select(func.count(ProductThesis.id))
    if status is not None:
        query = query.where(ProductThesis.status == status)
        count_query = count_query.where(ProductThesis.status == status)
    total = await db.scalar(count_query) or 0
    theses = await db.scalars(
        query.order_by(ProductThesis.updated_at.desc(), ProductThesis.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return ProductThesisListResponse(
        items=list(theses), total=total, page=page, page_size=page_size
    )


@router.get("/{thesis_id}/workbench", response_model=ProductThesisWorkbenchResponse)
async def get_product_thesis_workbench(
    thesis_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
):
    thesis = await _thesis_or_404(db, thesis_id)
    observations = list(
        await db.scalars(
            select(ProductThesisObservation)
            .where(ProductThesisObservation.product_thesis_id == thesis.id)
            .order_by(ProductThesisObservation.created_at)
        )
    )
    authorization = await db.scalar(
        select(BuildAuthorization).where(BuildAuthorization.product_thesis_id == thesis.id)
    )
    gaps: list[str] = []
    if not observations:
        gaps.append("record an observation before making a Product Thesis decision")
    if thesis.status != "decided":
        gaps.append("record an explicit continue, change, or stop decision")
    elif thesis.decision == "continue" and authorization is None:
        gaps.append("record a build authorization before defining a Feature")
    return {
        "product_thesis": thesis,
        "observations": observations,
        "build_authorization": authorization,
        "gaps": gaps,
    }


@router.post(
    "/{thesis_id}/observations", response_model=ProductThesisObservationResponse, status_code=201
)
async def record_observation(
    thesis_id: uuid.UUID,
    body: ProductThesisObservationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    thesis = await _thesis_or_404(db, thesis_id)
    if thesis.status == "decided":
        raise HTTPException(
            status_code=409, detail="A decided Product Thesis cannot receive new observations"
        )
    observation = ProductThesisObservation(product_thesis_id=thesis.id, **body.model_dump())
    db.add(observation)
    await db.commit()
    await db.refresh(observation)
    return observation


@router.post(
    "/{thesis_id}/build-authorization", response_model=BuildAuthorizationResponse, status_code=201
)
async def authorize_build(
    thesis_id: uuid.UUID,
    body: BuildAuthorizationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    thesis = await _thesis_or_404(db, thesis_id)
    if thesis.status != "decided" or thesis.decision != "continue":
        raise HTTPException(
            status_code=409,
            detail="A build authorization requires a continuing Product Thesis decision",
        )
    existing = await db.scalar(
        select(BuildAuthorization).where(BuildAuthorization.product_thesis_id == thesis.id)
    )
    if existing is not None:
        raise HTTPException(
            status_code=409, detail="This Product Thesis already has a build authorization"
        )
    authorization = BuildAuthorization(product_thesis_id=thesis.id, rationale=body.rationale)
    db.add(authorization)
    await db.commit()
    await db.refresh(authorization)
    return authorization


@router.post("/{thesis_id}/decision", response_model=ProductThesisResponse)
async def decide_thesis(
    thesis_id: uuid.UUID, body: ProductThesisDecision, db: Annotated[AsyncSession, Depends(get_db)]
):
    thesis = await _thesis_or_404(db, thesis_id)
    count = await db.scalar(
        select(func.count(ProductThesisObservation.id)).where(
            ProductThesisObservation.product_thesis_id == thesis.id
        )
    )
    if not count:
        raise HTTPException(
            status_code=409,
            detail="A Product Thesis decision requires at least one offer observation",
        )
    thesis.status = "decided"
    thesis.decision, thesis.decision_rationale = body.decision, body.rationale
    await db.commit()
    await db.refresh(thesis)
    return thesis
