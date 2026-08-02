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
    NeedChallengeCreate,
    NeedChallengeResponse,
    NeedEvidenceCreate,
    NeedEvidenceResponse,
    NeedIssueCreate,
    NeedIssueFromAcceptedSignalCreate,
    NeedIssueResponse,
    NeedIssueTransition,
    NeedIssueUpdate,
    ProductThesisCreate,
    ProductThesisResponse,
    ValidationExperimentCreate,
    ValidationExperimentResponse,
)
from packages.storage.models.external_signal import ExternalSignal
from packages.storage.models.need_issue import (
    BuildAuthorization,
    FeatureDefinition,
    NeedChallenge,
    NeedEvidence,
    NeedIssue,
    NeedIssueStatusEvent,
    NeedIssueVersion,
    ProductThesis,
    ValidationExperiment,
)

router = APIRouter()

_ALLOWED_TRANSITIONS = {
    "captured": {"triaged", "evidence-backed", "discovery-validated", "rejected", "dormant"},
    "triaged": {"captured", "evidence-backed", "discovery-validated", "rejected", "dormant"},
    "evidence-backed": {"triaged", "discovery-validated", "rejected", "dormant"},
    "discovery-validated": {"feature-defined", "rejected", "dormant"},
    "feature-defined": {"in-development", "rejected", "dormant"},
    "in-development": {"review-ready", "rejected", "dormant"},
    "review-ready": {"merged", "in-development", "rejected", "dormant"},
    "merged": {"released", "rejected", "dormant"},
    "released": {"measured", "rejected", "dormant"},
    "measured": {"retained", "rejected", "dormant"},
    "retained": {"dormant"},
    "dormant": {"captured", "triaged", "evidence-backed"},
    "rejected": {"captured"},
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


def _snapshot(need_issue: NeedIssue) -> dict:
    return {
        field: getattr(need_issue, field)
        for field in (
            "title",
            "target_actor",
            "context",
            "problem",
            "desired_outcome",
            "workaround",
            "counterevidence_summary",
            "unknowns",
            "next_validation_action",
        )
    }


async def _add_evidence(
    db: AsyncSession, need_issue_id: uuid.UUID, body: NeedEvidenceCreate
) -> NeedEvidence:
    if body.external_signal_id is not None:
        signal = await db.get(ExternalSignal, body.external_signal_id)
        if signal is None:
            raise HTTPException(status_code=422, detail="External Signal not found")
    evidence = NeedEvidence(need_issue_id=need_issue_id, **body.model_dump())
    db.add(evidence)
    return evidence


async def _discovery_gate_gaps(db: AsyncSession, need_issue: NeedIssue) -> list[str]:
    supporting = await db.scalar(
        select(func.count(NeedEvidence.id)).where(
            NeedEvidence.need_issue_id == need_issue.id, NeedEvidence.role == "supporting"
        )
    )
    counter = await db.scalar(
        select(func.count(NeedEvidence.id)).where(
            NeedEvidence.need_issue_id == need_issue.id, NeedEvidence.role == "counter"
        )
    )
    challenges = await db.scalar(
        select(func.count(NeedChallenge.id)).where(NeedChallenge.need_issue_id == need_issue.id)
    )
    gaps = []
    if not supporting:
        gaps.append("supporting evidence")
    if not counter:
        gaps.append("counter evidence")
    if not need_issue.unknowns:
        gaps.append("unknowns")
    if not need_issue.next_validation_action.strip():
        gaps.append("next validation action")
    if not challenges:
        gaps.append("challenge")
    return gaps


@router.post("", response_model=NeedIssueResponse, status_code=201)
async def create_need_issue(body: NeedIssueCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    need_issue = NeedIssue(**body.model_dump())
    db.add(need_issue)
    await db.flush()
    db.add(
        NeedIssueVersion(
            need_issue_id=need_issue.id,
            version=1,
            snapshot=_snapshot(need_issue),
            change_reason="Initial definition",
        )
    )
    await db.commit()
    await db.refresh(need_issue)
    return await _response(need_issue, db)


@router.get("/{need_issue_id}", response_model=NeedIssueResponse)
async def get_need_issue(need_issue_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    return await _response(await _get_need_issue_or_404(db, need_issue_id), db)


@router.get("/{need_issue_id}/asset-ledger")
async def get_need_issue_asset_ledger(
    need_issue_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
):
    need_issue = await _get_need_issue_or_404(db, need_issue_id)
    evidence = list(
        await db.scalars(select(NeedEvidence).where(NeedEvidence.need_issue_id == need_issue.id))
    )
    challenges = list(
        await db.scalars(select(NeedChallenge).where(NeedChallenge.need_issue_id == need_issue.id))
    )
    experiments = list(
        await db.scalars(
            select(ValidationExperiment).where(ValidationExperiment.need_issue_id == need_issue.id)
        )
    )
    theses = list(
        await db.scalars(select(ProductThesis).where(ProductThesis.need_issue_id == need_issue.id))
    )
    gaps = []
    if not any(item.role == "supporting" for item in evidence):
        gaps.append("supporting evidence")
    if not any(item.role == "counter" for item in evidence):
        gaps.append("counter evidence")
    if not challenges:
        gaps.append("challenge")
    if not experiments:
        gaps.append("validation experiment")
    return {
        "need_issue_id": need_issue.id,
        "status": need_issue.status,
        "evidence": evidence,
        "challenges": challenges,
        "experiments": experiments,
        "product_theses": theses,
        "gaps": gaps,
    }


@router.post("/from-accepted-signal", response_model=NeedIssueResponse, status_code=201)
async def create_need_issue_from_accepted_signal(
    body: NeedIssueFromAcceptedSignalCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    signal = await db.get(ExternalSignal, body.external_signal_id)
    if signal is None:
        raise HTTPException(status_code=422, detail="External Signal not found")
    if signal.status != "accepted":
        raise HTTPException(
            status_code=409,
            detail="External Signal must be accepted before it can seed a Need Issue",
        )

    need_issue = NeedIssue(**body.model_dump(exclude={"external_signal_id", "excerpt"}))
    db.add(need_issue)
    await db.flush()
    db.add(
        NeedIssueVersion(
            need_issue_id=need_issue.id,
            version=1,
            snapshot=_snapshot(need_issue),
            change_reason="Initial definition from accepted external signal",
        )
    )
    db.add(
        NeedEvidence(
            need_issue_id=need_issue.id,
            reference_type="external_signal",
            reference_uri=signal.source_uri or f"external-signal://{signal.id}",
            external_signal_id=signal.id,
            role="supporting",
            excerpt=body.excerpt or signal.observation,
        )
    )
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
    evidence = await _add_evidence(db, need_issue_id, body)
    await db.commit()
    await db.refresh(evidence)
    return evidence


@router.post("/{need_issue_id}/challenges", response_model=NeedChallengeResponse, status_code=201)
async def add_challenge(
    need_issue_id: uuid.UUID,
    body: NeedChallengeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _get_need_issue_or_404(db, need_issue_id)
    challenge = NeedChallenge(need_issue_id=need_issue_id, **body.model_dump())
    db.add(challenge)
    await db.commit()
    await db.refresh(challenge)
    return challenge


@router.post(
    "/{need_issue_id}/experiments", response_model=ValidationExperimentResponse, status_code=201
)
async def create_validation_experiment(
    need_issue_id: uuid.UUID,
    body: ValidationExperimentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    need_issue = await _get_need_issue_or_404(db, need_issue_id)
    active_count = await db.scalar(
        select(func.count(ValidationExperiment.id)).where(
            ValidationExperiment.status.in_(["draft", "approved", "running"])
        )
    )
    if (active_count or 0) >= 3 and body.wip_override_reason is None:
        raise HTTPException(
            status_code=409,
            detail="Validation WIP limit is 3; an operator override reason is required",
        )
    experiment = ValidationExperiment(need_issue_id=need_issue.id, **body.model_dump())
    db.add(experiment)
    await db.commit()
    await db.refresh(experiment)
    return experiment


@router.post(
    "/{need_issue_id}/product-theses", response_model=ProductThesisResponse, status_code=201
)
async def create_product_thesis(
    need_issue_id: uuid.UUID,
    body: ProductThesisCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    need_issue = await _get_need_issue_or_404(db, need_issue_id)
    if need_issue.status != "discovery-validated":
        raise HTTPException(
            status_code=409,
            detail="Need Issue must be discovery-validated before a Product Thesis can be created",
        )
    thesis = ProductThesis(need_issue_id=need_issue.id, **body.model_dump())
    db.add(thesis)
    await db.commit()
    await db.refresh(thesis)
    return thesis


@router.patch("/{need_issue_id}", response_model=NeedIssueResponse)
async def update_need_issue(
    need_issue_id: uuid.UUID,
    body: NeedIssueUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    need_issue = await _get_need_issue_or_404(db, need_issue_id)
    changes = body.model_dump(exclude={"change_reason"}, exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one definition field must change")
    for field, value in changes.items():
        setattr(need_issue, field, value)
    need_issue.definition_version += 1
    db.add(
        NeedIssueVersion(
            need_issue_id=need_issue.id,
            version=need_issue.definition_version,
            snapshot=_snapshot(need_issue),
            change_reason=body.change_reason,
        )
    )
    await db.commit()
    await db.refresh(need_issue)
    return await _response(need_issue, db)


@router.get("/{need_issue_id}/versions")
async def list_need_issue_versions(
    need_issue_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
):
    await _get_need_issue_or_404(db, need_issue_id)
    versions = await db.scalars(
        select(NeedIssueVersion)
        .where(NeedIssueVersion.need_issue_id == need_issue_id)
        .order_by(NeedIssueVersion.version)
    )
    return {
        "items": [
            {
                "version": item.version,
                "snapshot": item.snapshot,
                "change_reason": item.change_reason,
                "created_at": item.created_at,
            }
            for item in versions
        ]
    }


@router.get("/{need_issue_id}/status-events")
async def list_need_issue_status_events(
    need_issue_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
):
    await _get_need_issue_or_404(db, need_issue_id)
    events = await db.scalars(
        select(NeedIssueStatusEvent)
        .where(NeedIssueStatusEvent.need_issue_id == need_issue_id)
        .order_by(NeedIssueStatusEvent.created_at)
    )
    return {
        "items": [
            {
                "from_status": item.from_status,
                "to_status": item.to_status,
                "reason": item.reason,
                "created_at": item.created_at,
            }
            for item in events
        ]
    }


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
    requires_reason = target in {"dormant", "rejected"} or need_issue.status in {
        "dormant",
        "rejected",
    }
    if requires_reason and body.reason is None:
        raise HTTPException(status_code=422, detail="This status change requires a recorded reason")
    if need_issue.status in {"dormant", "rejected"} and body.new_evidence is None:
        raise HTTPException(status_code=422, detail="Reopening requires a new evidence reference")
    if target == "discovery-validated":
        gaps = await _discovery_gate_gaps(db, need_issue)
        if gaps and not body.override_gate:
            raise HTTPException(
                status_code=409,
                detail=f"Discovery validation gate is incomplete: {', '.join(gaps)}",
            )
        if body.override_gate and body.reason is None:
            raise HTTPException(status_code=422, detail="Gate override requires a recorded reason")
    previous = need_issue.status
    need_issue.status = target
    if body.new_evidence is not None:
        await _add_evidence(db, need_issue.id, body.new_evidence)
    db.add(
        NeedIssueStatusEvent(
            need_issue_id=need_issue.id,
            from_status=previous,
            to_status=target,
            reason=(f"OVERRIDE: {body.reason}" if body.override_gate else body.reason)
            or "Status transition",
        )
    )
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
    thesis = await db.get(ProductThesis, body.product_thesis_id)
    if thesis is None or thesis.need_issue_id != need_issue.id:
        raise HTTPException(
            status_code=422,
            detail="Feature Definition must reference a Product Thesis for this Need Issue",
        )
    authorization = await db.scalar(
        select(BuildAuthorization).where(BuildAuthorization.product_thesis_id == thesis.id)
    )
    if authorization is None:
        raise HTTPException(
            status_code=409, detail="Feature Definition requires a recorded build authorization"
        )
    feature = FeatureDefinition(need_issue_id=need_issue.id, **body.model_dump())
    need_issue.status = "feature-defined"
    db.add(feature)
    await db.commit()
    await db.refresh(feature)
    return feature
