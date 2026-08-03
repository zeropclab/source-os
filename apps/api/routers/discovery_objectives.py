"""Create and read operator-bounded Discovery Objectives."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.dependencies import get_db
from apps.api.schemas.discovery_objective import (
    AcquisitionPlanCreate,
    AcquisitionPlanResponse,
    ApprovedCollectionBoundaryResponse,
    BoundaryPatch,
    DiscoveryObjectiveCreate,
    DiscoveryObjectiveResponse,
    DiscoveryObjectiveWorkspaceResponse,
    ObjectiveBlockRequest,
    OperatorApprovalCreate,
    OperatorApprovalDecision,
    OperatorApprovalResponse,
    OperatorBoundaryRevisionCreate,
    OperatorBoundaryRevisionResponse,
    PlanRevisionResponse,
)
from packages.storage.models.acquisition_plan import AcquisitionPlan, PlanRevision
from packages.storage.models.discovery_objective import (
    ApprovedCollectionBoundary,
    DiscoveryObjective,
    OperatorApproval,
    OperatorBoundaryRevision,
)
from packages.storage.models.source import Source

router = APIRouter()


def _objective_with_boundaries(objective_id: uuid.UUID):
    return (
        select(DiscoveryObjective)
        .options(selectinload(DiscoveryObjective.boundaries))
        .where(DiscoveryObjective.id == objective_id)
    )


def _plan_with_missions(plan_id: uuid.UUID):
    return (
        select(AcquisitionPlan)
        .options(selectinload(AcquisitionPlan.missions))
        .where(AcquisitionPlan.id == plan_id)
    )


def _response_for(objective: DiscoveryObjective) -> DiscoveryObjectiveResponse:
    current_boundary = objective.boundaries[-1]
    return DiscoveryObjectiveResponse(
        id=objective.id,
        title=objective.title,
        question=objective.question,
        resource_stop_conditions=objective.resource_stop_conditions,
        evidence_stop_conditions=objective.evidence_stop_conditions,
        decision_stop_conditions=objective.decision_stop_conditions,
        status=objective.status,
        created_at=objective.created_at,
        updated_at=objective.updated_at,
        current_boundary=ApprovedCollectionBoundaryResponse.model_validate(current_boundary),
    )


def _boundary_response(boundary: ApprovedCollectionBoundary) -> ApprovedCollectionBoundaryResponse:
    return ApprovedCollectionBoundaryResponse.model_validate(boundary)


def _revision_response(
    revision: OperatorBoundaryRevision, boundary_version: int
) -> OperatorBoundaryRevisionResponse:
    return OperatorBoundaryRevisionResponse(
        id=revision.id,
        objective_id=revision.objective_id,
        boundary_id=revision.boundary_id,
        boundary_version=boundary_version,
        approval_id=revision.approval_id,
        operator=revision.operator,
        reason=revision.reason,
        boundary_patch=revision.boundary_patch,
        created_at=revision.created_at,
    )


async def _plan_response(db: AsyncSession, plan: AcquisitionPlan) -> AcquisitionPlanResponse:
    revision = await db.scalar(select(PlanRevision).where(PlanRevision.plan_id == plan.id))
    boundary = await db.scalar(
        select(ApprovedCollectionBoundary).where(ApprovedCollectionBoundary.id == plan.boundary_id)
    )
    return AcquisitionPlanResponse(
        id=plan.id,
        objective_id=plan.objective_id,
        boundary_id=plan.boundary_id,
        boundary_version=boundary.version,
        version=plan.version,
        question=plan.question,
        selected_source_ids=plan.selected_source_ids,
        counterevidence_target=plan.counterevidence_target,
        request_budget=plan.request_budget,
        time_budget_minutes=plan.time_budget_minutes,
        cost_budget_cents=plan.cost_budget_cents,
        created_at=plan.created_at,
        predecessor_plan_id=revision.predecessor_plan_id if revision else None,
        revision=(
            PlanRevisionResponse(
                id=revision.id,
                predecessor_plan_id=revision.predecessor_plan_id,
                reason=revision.reason,
                delta=revision.delta,
                created_at=revision.created_at,
            )
            if revision
            else None
        ),
        missions=[mission.id for mission in plan.missions],
    )


async def _validate_source_ids(db: AsyncSession, source_ids: list[uuid.UUID]) -> None:
    if len(set(source_ids)) != len(source_ids):
        raise HTTPException(status_code=422, detail="Approved source IDs must not repeat")
    found_source_ids = set(
        (await db.scalars(select(Source.id).where(Source.id.in_(source_ids)))).all()
    )
    if found_source_ids != set(source_ids):
        raise HTTPException(status_code=422, detail="An approved source does not exist")


async def _apply_boundary_patch(
    db: AsyncSession,
    objective: DiscoveryObjective,
    current: ApprovedCollectionBoundary,
    patch: BoundaryPatch,
) -> tuple[ApprovedCollectionBoundary, dict]:
    values = patch.model_dump(exclude_none=True)
    if not values:
        raise HTTPException(status_code=422, detail="Boundary revision requires a material delta")
    if "approved_source_ids" in values:
        await _validate_source_ids(db, values["approved_source_ids"])
        values["approved_source_ids"] = [
            str(source_id) for source_id in values["approved_source_ids"]
        ]

    current_values = {
        "approved_source_ids": current.approved_source_ids,
        "tool_allowlist": current.tool_allowlist,
        "request_limit": current.request_limit,
        "time_budget_minutes": current.time_budget_minutes,
        "cost_budget_cents": current.cost_budget_cents,
        "credential_scope": current.credential_scope,
        "evidence_conditions": current.evidence_conditions,
    }
    if all(current_values[key] == value for key, value in values.items()):
        raise HTTPException(status_code=422, detail="Boundary revision must change an allowance")

    next_values = current_values | values
    boundary = ApprovedCollectionBoundary(
        objective=objective,
        version=current.version + 1,
        **next_values,
    )
    db.add(boundary)
    await db.flush()
    return boundary, values


@router.post("", response_model=DiscoveryObjectiveResponse, status_code=201)
async def create_discovery_objective(
    body: DiscoveryObjectiveCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    source_ids = body.initial_boundary.approved_source_ids
    await _validate_source_ids(db, source_ids)

    objective = DiscoveryObjective(
        title=body.title,
        question=body.question,
        resource_stop_conditions=body.resource_stop_conditions,
        evidence_stop_conditions=body.evidence_stop_conditions,
        decision_stop_conditions=body.decision_stop_conditions,
    )
    boundary = ApprovedCollectionBoundary(
        objective=objective,
        version=1,
        approved_source_ids=[str(source_id) for source_id in source_ids],
        tool_allowlist=body.initial_boundary.tool_allowlist,
        request_limit=body.initial_boundary.request_limit,
        time_budget_minutes=body.initial_boundary.time_budget_minutes,
        cost_budget_cents=body.initial_boundary.cost_budget_cents,
        credential_scope=body.initial_boundary.credential_scope,
        evidence_conditions=body.initial_boundary.evidence_conditions,
    )
    db.add_all([objective, boundary])
    await db.commit()
    saved = await db.scalar(_objective_with_boundaries(objective.id))
    return _response_for(saved)


@router.get("/{objective_id}", response_model=DiscoveryObjectiveResponse)
async def get_discovery_objective(
    objective_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    objective = await db.scalar(_objective_with_boundaries(objective_id))
    if objective is None:
        raise HTTPException(status_code=404, detail="Discovery Objective not found")
    return _response_for(objective)


@router.get("/{objective_id}/workspace", response_model=DiscoveryObjectiveWorkspaceResponse)
async def get_discovery_objective_workspace(
    objective_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    objective = await db.scalar(_objective_with_boundaries(objective_id))
    if objective is None:
        raise HTTPException(status_code=404, detail="Discovery Objective not found")
    response = _response_for(objective)
    plans = list(
        (
            await db.scalars(
                select(AcquisitionPlan)
                .options(selectinload(AcquisitionPlan.missions))
                .where(AcquisitionPlan.objective_id == objective_id)
                .order_by(AcquisitionPlan.version.desc())
            )
        ).all()
    )
    return DiscoveryObjectiveWorkspaceResponse(
        objective=response,
        current_boundary=response.current_boundary,
        plans=[await _plan_response(db, plan) for plan in plans],
        pending_approvals=list(
            (
                await db.scalars(
                    select(OperatorApproval)
                    .where(
                        OperatorApproval.objective_id == objective_id,
                        OperatorApproval.status == "pending",
                    )
                    .order_by(OperatorApproval.created_at.desc())
                )
            ).all()
        ),
        boundary_revisions=[
            _revision_response(revision, boundary.version)
            for revision, boundary in (
                await db.execute(
                    select(OperatorBoundaryRevision, ApprovedCollectionBoundary)
                    .join(
                        ApprovedCollectionBoundary,
                        OperatorBoundaryRevision.boundary_id == ApprovedCollectionBoundary.id,
                    )
                    .where(OperatorBoundaryRevision.objective_id == objective_id)
                    .order_by(OperatorBoundaryRevision.created_at.desc())
                )
            ).all()
        ],
    )


@router.post("/{objective_id}/plans", response_model=AcquisitionPlanResponse, status_code=201)
async def create_acquisition_plan(
    objective_id: uuid.UUID,
    body: AcquisitionPlanCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    objective = await db.scalar(_objective_with_boundaries(objective_id))
    if objective is None:
        raise HTTPException(status_code=404, detail="Discovery Objective not found")
    if objective.status != "active":
        raise HTTPException(status_code=409, detail="Only an active objective can create a plan")

    current_boundary = objective.boundaries[-1]
    selected_source_ids = {str(source_id) for source_id in body.selected_source_ids}
    if len(selected_source_ids) != len(body.selected_source_ids):
        raise HTTPException(status_code=422, detail="Plan source IDs must not repeat")
    if not selected_source_ids.issubset(set(current_boundary.approved_source_ids)):
        raise HTTPException(
            status_code=422,
            detail="Plan sources are outside the approved boundary",
        )
    if (
        body.request_budget > current_boundary.request_limit
        or body.time_budget_minutes > current_boundary.time_budget_minutes
        or body.cost_budget_cents > current_boundary.cost_budget_cents
    ):
        raise HTTPException(status_code=422, detail="Plan budget is outside the approved boundary")

    latest_version = await db.scalar(
        select(func.max(AcquisitionPlan.version)).where(
            AcquisitionPlan.objective_id == objective_id
        )
    )
    if body.predecessor_plan_id is not None:
        predecessor = await db.scalar(_plan_with_missions(body.predecessor_plan_id))
        if predecessor is None or predecessor.objective_id != objective_id:
            raise HTTPException(
                status_code=422,
                detail="Plan predecessor does not belong to this objective",
            )
        if not body.revision_reason or body.revision_delta is None:
            raise HTTPException(status_code=422, detail="Plan revision requires a reason and delta")
    elif body.revision_reason or body.revision_delta is not None:
        raise HTTPException(status_code=422, detail="Initial plan cannot include a revision record")

    plan = AcquisitionPlan(
        objective_id=objective_id,
        boundary_id=current_boundary.id,
        version=(latest_version or 0) + 1,
        question=body.question,
        selected_source_ids=[str(source_id) for source_id in body.selected_source_ids],
        counterevidence_target=body.counterevidence_target,
        request_budget=body.request_budget,
        time_budget_minutes=body.time_budget_minutes,
        cost_budget_cents=body.cost_budget_cents,
    )
    db.add(plan)
    await db.flush()
    if body.predecessor_plan_id is not None:
        revision = PlanRevision(
            plan_id=plan.id,
            predecessor_plan_id=body.predecessor_plan_id,
            reason=body.revision_reason,
            delta=body.revision_delta,
        )
        db.add(revision)
    await db.commit()
    saved = await db.scalar(_plan_with_missions(plan.id))
    return await _plan_response(db, saved)


@router.post("/{objective_id}/approvals", response_model=OperatorApprovalResponse, status_code=201)
async def request_operator_approval(
    objective_id: uuid.UUID,
    body: OperatorApprovalCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    objective = await db.scalar(_objective_with_boundaries(objective_id))
    if objective is None:
        raise HTTPException(status_code=404, detail="Discovery Objective not found")
    if objective.status != "active":
        raise HTTPException(status_code=409, detail="Only an active objective can request approval")
    if not body.requested_boundary_patch.model_dump(exclude_none=True):
        raise HTTPException(status_code=422, detail="Approval request requires a boundary delta")

    approval = OperatorApproval(
        objective_id=objective_id,
        request_type=body.request_type,
        reason=body.reason,
        requested_boundary_patch=body.requested_boundary_patch.model_dump(
            exclude_none=True, mode="json"
        ),
    )
    objective.status = "pending_approval"
    db.add(approval)
    await db.commit()
    return approval


@router.post(
    "/{objective_id}/approvals/{approval_id}/approve",
    response_model=OperatorApprovalResponse,
)
async def approve_operator_request(
    objective_id: uuid.UUID,
    approval_id: uuid.UUID,
    body: OperatorApprovalDecision,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    objective = await db.scalar(_objective_with_boundaries(objective_id))
    approval = await db.scalar(
        select(OperatorApproval).where(
            OperatorApproval.id == approval_id,
            OperatorApproval.objective_id == objective_id,
        )
    )
    if objective is None or approval is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if objective.status != "pending_approval" or approval.status != "pending":
        raise HTTPException(status_code=409, detail="Approval request is not awaiting a decision")

    boundary, normalized_patch = await _apply_boundary_patch(
        db,
        objective,
        objective.boundaries[-1],
        BoundaryPatch.model_validate(approval.requested_boundary_patch),
    )
    revision = OperatorBoundaryRevision(
        objective_id=objective_id,
        boundary_id=boundary.id,
        approval_id=approval.id,
        operator=body.operator,
        reason=body.reason,
        boundary_patch=normalized_patch,
    )
    approval.status = "approved"
    approval.operator = body.operator
    approval.decision_reason = body.reason
    approval.decided_at = datetime.now(UTC)
    objective.status = "active"
    db.add(revision)
    await db.commit()
    return approval


@router.post(
    "/{objective_id}/approvals/{approval_id}/reject",
    response_model=OperatorApprovalResponse,
)
async def reject_operator_request(
    objective_id: uuid.UUID,
    approval_id: uuid.UUID,
    body: OperatorApprovalDecision,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    objective = await db.scalar(
        select(DiscoveryObjective).where(DiscoveryObjective.id == objective_id)
    )
    approval = await db.scalar(
        select(OperatorApproval).where(
            OperatorApproval.id == approval_id,
            OperatorApproval.objective_id == objective_id,
        )
    )
    if objective is None or approval is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if objective.status != "pending_approval" or approval.status != "pending":
        raise HTTPException(status_code=409, detail="Approval request is not awaiting a decision")

    approval.status = "rejected"
    approval.operator = body.operator
    approval.decision_reason = body.reason
    approval.decided_at = datetime.now(UTC)
    objective.status = "active"
    await db.commit()
    return approval


@router.post("/{objective_id}/block", response_model=DiscoveryObjectiveResponse)
async def block_discovery_objective(
    objective_id: uuid.UUID,
    body: ObjectiveBlockRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    objective = await db.scalar(_objective_with_boundaries(objective_id))
    if objective is None:
        raise HTTPException(status_code=404, detail="Discovery Objective not found")
    if objective.status != "active":
        raise HTTPException(status_code=409, detail="Only an active objective can become blocked")
    objective.status = "blocked"
    objective.block_reason = body.reason
    await db.commit()
    blocked = await db.scalar(_objective_with_boundaries(objective_id))
    return _response_for(blocked)


@router.post(
    "/{objective_id}/boundary-revisions",
    response_model=OperatorBoundaryRevisionResponse,
    status_code=201,
)
async def reactivate_with_boundary_revision(
    objective_id: uuid.UUID,
    body: OperatorBoundaryRevisionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    objective = await db.scalar(_objective_with_boundaries(objective_id))
    if objective is None:
        raise HTTPException(status_code=404, detail="Discovery Objective not found")
    if objective.status != "blocked":
        raise HTTPException(
            status_code=409,
            detail="Boundary revision can reactivate only a blocked objective",
        )

    boundary, normalized_patch = await _apply_boundary_patch(
        db, objective, objective.boundaries[-1], body.boundary_patch
    )
    revision = OperatorBoundaryRevision(
        objective_id=objective_id,
        boundary_id=boundary.id,
        operator=body.operator,
        reason=body.reason,
        boundary_patch=normalized_patch,
    )
    objective.status = "active"
    objective.block_reason = None
    db.add(revision)
    await db.commit()
    return _revision_response(revision, boundary.version)
