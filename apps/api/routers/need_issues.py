"""Internal Need Issues: evidence before product-definition work."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from apps.api.schemas.need_issue import (
    FeatureDefinitionCreate,
    FeatureDefinitionResponse,
    NeedEvidenceCreate,
    NeedEvidenceResponse,
    NeedIssueCreate,
    NeedIssueResponse,
    NeedIssueTransition,
)
from packages.storage.models.need_issue import FeatureDefinition, NeedEvidence, NeedIssue

router = APIRouter()

_ALLOWED_TRANSITIONS = {
    "captured": {"triaged", "evidence-backed", "discovery-validated", "rejected"},
    "triaged": {"captured", "evidence-backed", "discovery-validated", "rejected"},
    "evidence-backed": {"triaged", "discovery-validated", "rejected"},
    "discovery-validated": {"feature-defined", "rejected"},
    "feature-defined": {"in-development", "rejected"},
    "in-development": {"review-ready", "rejected"},
    "review-ready": {"merged", "in-development", "rejected"},
    "merged": {"released", "rejected"},
    "released": {"measured", "rejected"},
    "measured": {"retained", "rejected"},
    "retained": set(),
    "rejected": set(),
}


async def _get_need_issue_or_404(db: AsyncSession, need_issue_id: uuid.UUID) -> NeedIssue:
    result = await db.execute(select(NeedIssue).where(NeedIssue.id == need_issue_id))
    need_issue = result.scalar_one_or_none()
    if need_issue is None:
        raise HTTPException(status_code=404, detail="Need Issue not found")
    return need_issue


async def _response(need_issue: NeedIssue, db: AsyncSession) -> NeedIssueResponse:
    evidence_count = await db.scalar(
        select(func.count(NeedEvidence.id)).where(NeedEvidence.need_issue_id == need_issue.id)
    )
    response = NeedIssueResponse.model_validate(need_issue, from_attributes=True)
    return response.model_copy(update={"evidence_count": evidence_count or 0})


@router.post("", response_model=NeedIssueResponse, status_code=201)
async def create_need_issue(body: NeedIssueCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    need_issue = NeedIssue(**body.model_dump())
    db.add(need_issue)
    await db.commit()
    await db.refresh(need_issue)
    return await _response(need_issue, db)


@router.post("/{need_issue_id}/evidence", response_model=NeedEvidenceResponse, status_code=201)
async def add_evidence(
    need_issue_id: uuid.UUID,
    body: NeedEvidenceCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _get_need_issue_or_404(db, need_issue_id)
    evidence = NeedEvidence(need_issue_id=need_issue_id, **body.model_dump())
    db.add(evidence)
    await db.commit()
    await db.refresh(evidence)
    return evidence


@router.post("/{need_issue_id}/transition", response_model=NeedIssueResponse)
async def transition_need_issue(
    need_issue_id: uuid.UUID,
    body: NeedIssueTransition,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    need_issue = await _get_need_issue_or_404(db, need_issue_id)
    target = body.status
    if target not in _ALLOWED_TRANSITIONS[need_issue.status]:
        raise HTTPException(
            status_code=409,
            detail=f"Need Issue must be discovery-validated before it can become {target}",
        )
    if target == "discovery-validated":
        supporting_count = await db.scalar(
            select(func.count(NeedEvidence.id)).where(
                NeedEvidence.need_issue_id == need_issue.id,
                NeedEvidence.role == "supporting",
            )
        )
        if not supporting_count:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Need Issue needs at least one supporting evidence reference "
                    "before discovery validation"
                ),
            )
    need_issue.status = target
    await db.commit()
    await db.refresh(need_issue)
    return await _response(need_issue, db)


@router.post("/{need_issue_id}/features", response_model=FeatureDefinitionResponse, status_code=201)
async def create_feature_definition(
    need_issue_id: uuid.UUID,
    body: FeatureDefinitionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    need_issue = await _get_need_issue_or_404(db, need_issue_id)
    if need_issue.status != "discovery-validated":
        raise HTTPException(
            status_code=409,
            detail=(
                "Need Issue must be discovery-validated before a feature definition can be created"
            ),
        )
    feature = FeatureDefinition(need_issue_id=need_issue.id, **body.model_dump())
    need_issue.status = "feature-defined"
    db.add(feature)
    await db.commit()
    await db.refresh(feature)
    return feature

