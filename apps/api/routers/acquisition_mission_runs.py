"""Execute pinned Acquisition Missions and retrieve their lineage."""

import asyncio
import copy
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from apps.api.dependencies import (
    get_db,
    get_github_live_transport,
    get_github_mission_transport,
)
from apps.api.schemas.acquisition_mission import AcquisitionMissionResponse
from apps.api.schemas.acquisition_mission_run import (
    AcquisitionMissionDryRunCreate,
    AcquisitionMissionRunControl,
    AcquisitionMissionRunCreate,
    AcquisitionMissionRunListResponse,
    AcquisitionMissionRunResponse,
)
from packages.adapters.github_mission import (
    BoundedGitHubMissionTransport,
    ContextCompleteness,
    GitHubArtifactReplayTransport,
    GitHubMissionAdapter,
    GitHubMissionResult,
    GitHubMissionTransport,
    SignalDraft,
)
from packages.storage.models.acquisition_mission import AcquisitionMission
from packages.storage.models.acquisition_mission_run import AcquisitionMissionRun
from packages.storage.models.acquisition_mission_run_signal import (
    AcquisitionMissionRunSignal,
)
from packages.storage.models.acquisition_plan import AcquisitionPlan
from packages.storage.models.discovery_objective import (
    ApprovedCollectionBoundary,
    DiscoveryObjective,
)
from packages.storage.models.external_signal import ExternalSignal
from packages.storage.models.source import Source

router = APIRouter()
read_router = APIRouter()


async def _get_mission_or_404(db: AsyncSession, mission_id: uuid.UUID) -> AcquisitionMission:
    mission = await db.scalar(
        select(AcquisitionMission)
        .options(joinedload(AcquisitionMission.source_config_version))
        .where(AcquisitionMission.id == mission_id)
    )
    if mission is None:
        raise HTTPException(status_code=404, detail="Acquisition Mission not found")
    if mission.source_config_version_id is None or mission.source_config_version is None:
        raise HTTPException(
            status_code=422, detail="Acquisition Mission has no pinned source version"
        )
    if mission.acquisition_plan_id is not None:
        plan = await db.get(AcquisitionPlan, mission.acquisition_plan_id)
        if plan is None:
            raise HTTPException(status_code=409, detail="Mission Plan is no longer available")
        objective = await db.get(DiscoveryObjective, plan.objective_id)
        current_boundary = await db.scalar(
            select(ApprovedCollectionBoundary)
            .where(ApprovedCollectionBoundary.objective_id == plan.objective_id)
            .order_by(ApprovedCollectionBoundary.version.desc())
        )
        if (
            objective is None
            or objective.status != "active"
            or current_boundary is None
            or plan.boundary_id != current_boundary.id
        ):
            raise HTTPException(
                status_code=409,
                detail="Plan is no longer permitted by the current approved boundary",
            )
    return mission


def _input_snapshot(mission: AcquisitionMission, source: Source) -> dict:
    mission_data = AcquisitionMissionResponse.model_validate(mission).model_dump(mode="json")
    config_data = mission_data.pop("source_config_version")
    return {
        "mission": mission_data,
        "source": {
            "id": str(source.id),
            "name": source.name,
            "platform": source.platform,
            "source_type": source.source_type,
            "url": source.url,
        },
        "source_config_version": config_data,
    }


async def _persist_signal_drafts(
    db: AsyncSession, run: AcquisitionMissionRun, drafts: list[SignalDraft]
) -> None:
    if not drafts:
        return
    await db.execute(
        insert(ExternalSignal)
        .values(
            [
                {
                    "id": uuid.uuid4(),
                    "mission_run_id": run.id,
                    "lineage_key": draft.lineage_key,
                    "raw_artifact_key": draft.raw_artifact_key,
                    "source_label": draft.source_label,
                    "source_uri": draft.source_uri,
                    "original_material": draft.original_material,
                    "observed_at": draft.observed_at,
                    "observation": draft.observation,
                    "interpretation": None,
                    "parent_context_available": draft.parent_context_available,
                    "context_snapshot": draft.context_snapshot,
                    "status": "candidate",
                }
                for draft in drafts
            ]
        )
        .on_conflict_do_nothing(index_elements=[ExternalSignal.lineage_key])
    )
    signal_rows = await db.scalars(
        select(ExternalSignal).where(
            ExternalSignal.lineage_key.in_([draft.lineage_key for draft in drafts])
        )
    )
    signals_by_lineage = {signal.lineage_key: signal for signal in signal_rows}
    run.external_signal_ids = [str(signals_by_lineage[draft.lineage_key].id) for draft in drafts]
    await db.execute(
        insert(AcquisitionMissionRunSignal)
        .values(
            [
                {
                    "run_id": run.id,
                    "signal_id": uuid.UUID(signal_id),
                    "ordinal": ordinal,
                }
                for ordinal, signal_id in enumerate(run.external_signal_ids)
            ]
        )
        .on_conflict_do_nothing(
            index_elements=[
                AcquisitionMissionRunSignal.run_id,
                AcquisitionMissionRunSignal.signal_id,
            ]
        )
    )


def _queued_run(
    mission: AcquisitionMission, source: Source, execution_mode: str
) -> AcquisitionMissionRun:
    config = mission.source_config_version
    return AcquisitionMissionRun(
        mission_id=mission.id,
        source_config_version_id=config.id,
        replay_of_run_id=None,
        execution_mode=execution_mode,
        lifecycle_status="queued",
        input_snapshot=_input_snapshot(mission, source),
        budgets={
            "request_limit": config.request_policy["request_limit"],
            "time_limit_seconds": config.request_policy["timeout_seconds"],
            "item_limit": mission.item_limit,
            "cost_budget_cents": mission.cost_budget_cents,
        },
        raw_artifacts=[],
        parser_version=(
            f"{config.extraction_settings['parser']}:{config.extraction_settings['parser_version']}"
        ),
        context_completeness={
            "issue": False,
            "comments": False,
            "parent_context": False,
            "pagination_complete": False,
            "missing": ["not_collected"],
        },
        checkpoints=["run:queued"],
        retry_count=0,
        terminal_state="not_started",
        failure_detail=None,
        transport_requests=0,
        network_requests=0,
        external_signal_ids=[],
    )


def _failed_timeout_result(timeout_seconds: int) -> GitHubMissionResult:
    return GitHubMissionResult(
        raw_artifacts=[],
        signals=[],
        context_completeness=ContextCompleteness(
            False,
            False,
            False,
            False,
            ("issue_page", "comments", "parent_context"),
        ),
        checkpoints=["run:timeout"],
        retry_count=0,
        terminal_state="failed",
        failure_detail=(f"Mission exceeded its {timeout_seconds} second time budget."),
    )


@router.post(
    "/{mission_id}/queued-runs",
    response_model=AcquisitionMissionRunResponse,
    status_code=201,
)
async def queue_acquisition_mission_run(
    mission_id: uuid.UUID,
    body: AcquisitionMissionRunCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Persist a pinned run plan without calling a source or creating evidence."""
    mission = await _get_mission_or_404(db, mission_id)
    source = await db.get(Source, mission.source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    run = _queued_run(mission, source, body.execution_mode)
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


@router.post(
    "/{mission_id}/dry-runs",
    response_model=AcquisitionMissionRunResponse,
    status_code=201,
)
async def create_acquisition_mission_dry_run(
    mission_id: uuid.UUID,
    body: AcquisitionMissionDryRunCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    fixture_transport: Annotated[GitHubMissionTransport, Depends(get_github_mission_transport)],
    live_transport: Annotated[GitHubMissionTransport, Depends(get_github_live_transport)],
):
    """Preview a bounded sample without promoting any material into the Evidence Inbox."""
    mission = await _get_mission_or_404(db, mission_id)
    source = await db.get(Source, mission.source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    config = mission.source_config_version
    if body.preview_item_limit > mission.item_limit:
        raise HTTPException(
            status_code=422,
            detail="Preview item limit cannot exceed the pinned mission item limit",
        )
    if body.preview_request_limit > config.request_policy["request_limit"]:
        raise HTTPException(
            status_code=422,
            detail="Preview request limit cannot exceed the pinned mission request limit",
        )

    selected_transport = live_transport if body.execution_mode == "live" else fixture_transport
    bounded_transport = BoundedGitHubMissionTransport(
        selected_transport,
        request_limit=body.preview_request_limit,
    )
    timeout_seconds = config.request_policy["timeout_seconds"]
    try:
        async with asyncio.timeout(timeout_seconds):
            result = await GitHubMissionAdapter().collect(
                source.url,
                config,
                bounded_transport,
                item_limit=body.preview_item_limit,
            )
    except TimeoutError:
        result = _failed_timeout_result(timeout_seconds)

    run = AcquisitionMissionRun(
        mission_id=mission.id,
        source_config_version_id=config.id,
        replay_of_run_id=None,
        execution_mode=f"dry_run:{body.execution_mode}",
        lifecycle_status="completed",
        input_snapshot=_input_snapshot(mission, source),
        budgets={
            "request_limit": body.preview_request_limit,
            "time_limit_seconds": timeout_seconds,
            "item_limit": body.preview_item_limit,
            "cost_budget_cents": mission.cost_budget_cents,
            "preview": True,
            "estimated_cost_cents": None,
            "estimated_cost_state": "unknown",
        },
        raw_artifacts=result.raw_artifacts,
        parser_version=(
            f"{config.extraction_settings['parser']}:{config.extraction_settings['parser_version']}"
        ),
        context_completeness=result.context_completeness.as_dict(),
        checkpoints=result.checkpoints,
        retry_count=result.retry_count,
        terminal_state=result.terminal_state,
        failure_detail=result.failure_detail,
        transport_requests=bounded_transport.transport_requests,
        network_requests=bounded_transport.network_requests,
        external_signal_ids=[],
        completed_at=func.now(),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


@router.post(
    "/{mission_id}/runs",
    response_model=AcquisitionMissionRunResponse,
    status_code=201,
)
async def create_acquisition_mission_run(
    mission_id: uuid.UUID,
    body: AcquisitionMissionRunCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    fixture_transport: Annotated[GitHubMissionTransport, Depends(get_github_mission_transport)],
    live_transport: Annotated[GitHubMissionTransport, Depends(get_github_live_transport)],
):
    mission = await _get_mission_or_404(db, mission_id)
    source = await db.get(Source, mission.source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    config = mission.source_config_version
    selected_transport = live_transport if body.execution_mode == "live" else fixture_transport
    bounded_transport = BoundedGitHubMissionTransport(
        selected_transport,
        request_limit=config.request_policy["request_limit"],
    )
    timeout_seconds = config.request_policy["timeout_seconds"]
    try:
        async with asyncio.timeout(timeout_seconds):
            result = await GitHubMissionAdapter().collect(
                source.url,
                config,
                bounded_transport,
                item_limit=mission.item_limit,
            )
    except TimeoutError:
        result = _failed_timeout_result(timeout_seconds)
    run = AcquisitionMissionRun(
        mission_id=mission.id,
        source_config_version_id=config.id,
        replay_of_run_id=None,
        execution_mode=body.execution_mode,
        lifecycle_status="completed",
        input_snapshot=_input_snapshot(mission, source),
        budgets={
            "request_limit": config.request_policy["request_limit"],
            "time_limit_seconds": config.request_policy["timeout_seconds"],
            "item_limit": mission.item_limit,
            "cost_budget_cents": mission.cost_budget_cents,
        },
        raw_artifacts=result.raw_artifacts,
        parser_version=(
            f"{config.extraction_settings['parser']}:{config.extraction_settings['parser_version']}"
        ),
        context_completeness=result.context_completeness.as_dict(),
        checkpoints=result.checkpoints,
        retry_count=result.retry_count,
        terminal_state=result.terminal_state,
        failure_detail=result.failure_detail,
        transport_requests=bounded_transport.transport_requests,
        network_requests=bounded_transport.network_requests,
        external_signal_ids=[],
        completed_at=func.now(),
    )
    db.add(run)
    await db.flush()
    await _persist_signal_drafts(db, run, result.signals)
    await db.commit()
    await db.refresh(run)
    return run


@router.get(
    "/{mission_id}/runs",
    response_model=AcquisitionMissionRunListResponse,
)
async def list_acquisition_mission_runs(
    mission_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    await _get_mission_or_404(db, mission_id)
    total = (
        await db.scalar(
            select(func.count(AcquisitionMissionRun.id)).where(
                AcquisitionMissionRun.mission_id == mission_id
            )
        )
        or 0
    )
    runs = await db.scalars(
        select(AcquisitionMissionRun)
        .where(AcquisitionMissionRun.mission_id == mission_id)
        .order_by(AcquisitionMissionRun.started_at.desc(), AcquisitionMissionRun.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return AcquisitionMissionRunListResponse(
        items=list(runs), total=total, page=page, page_size=page_size
    )


@read_router.post(
    "/{run_id}/replay",
    response_model=AcquisitionMissionRunResponse,
    status_code=201,
)
async def replay_acquisition_mission_run(
    run_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    original = await db.get(AcquisitionMissionRun, run_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Acquisition Mission run not found")
    mission = await _get_mission_or_404(db, original.mission_id)
    replay_result = await GitHubMissionAdapter().collect(
        original.input_snapshot["source"]["url"],
        mission.source_config_version,
        GitHubArtifactReplayTransport(copy.deepcopy(original.raw_artifacts)),
        item_limit=original.input_snapshot["mission"]["item_limit"],
    )
    original_signal_rows = await db.scalars(
        select(ExternalSignal).where(
            ExternalSignal.id.in_([uuid.UUID(value) for value in original.external_signal_ids])
        )
    )
    original_lineage_by_id = {str(signal.id): signal.lineage_key for signal in original_signal_rows}
    original_lineage = [original_lineage_by_id[value] for value in original.external_signal_ids]
    replay_lineage = [draft.lineage_key for draft in replay_result.signals]
    lineage_verified = replay_lineage == original_lineage
    replay = AcquisitionMissionRun(
        mission_id=original.mission_id,
        source_config_version_id=original.source_config_version_id,
        replay_of_run_id=original.id,
        execution_mode="fixture_replay",
        lifecycle_status="completed",
        input_snapshot=copy.deepcopy(original.input_snapshot),
        budgets=copy.deepcopy(original.budgets),
        raw_artifacts=copy.deepcopy(original.raw_artifacts),
        parser_version=original.parser_version,
        context_completeness=copy.deepcopy(original.context_completeness),
        checkpoints=[*copy.deepcopy(original.checkpoints), "replay:lineage_verified"],
        retry_count=original.retry_count,
        terminal_state=(original.terminal_state if lineage_verified else "failed"),
        failure_detail=(
            original.failure_detail
            if lineage_verified
            else "Replay lineage diverged from the original mission run."
        ),
        transport_requests=0,
        network_requests=0,
        external_signal_ids=[],
        completed_at=func.now(),
    )
    db.add(replay)
    await db.flush()
    if lineage_verified:
        await _persist_signal_drafts(db, replay, replay_result.signals)
    await db.commit()
    await db.refresh(replay)
    return replay


async def _control_queued_run(
    run_id: uuid.UUID,
    expected_statuses: tuple[str, ...],
    next_status: str,
    body: AcquisitionMissionRunControl,
    db: AsyncSession,
) -> AcquisitionMissionRun:
    run = await db.get(AcquisitionMissionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Acquisition Mission run not found")
    if run.lifecycle_status not in expected_statuses:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Run is {run.lifecycle_status}; expected "
                f"{' or '.join(expected_statuses)} for this control"
            ),
        )
    run.lifecycle_status = next_status
    run.control_reason = body.reason
    run.checkpoints = [*run.checkpoints, f"run:{next_status}"]
    if next_status == "cancelled":
        run.terminal_state = "cancelled"
        run.completed_at = func.now()
    await db.commit()
    await db.refresh(run)
    return run


@read_router.post("/{run_id}/pause", response_model=AcquisitionMissionRunResponse)
async def pause_acquisition_mission_run(
    run_id: uuid.UUID,
    body: AcquisitionMissionRunControl | None = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    return await _control_queued_run(
        run_id, ("queued", "scheduled"), "paused", body or AcquisitionMissionRunControl(), db
    )


@read_router.post("/{run_id}/resume", response_model=AcquisitionMissionRunResponse)
async def resume_acquisition_mission_run(
    run_id: uuid.UUID,
    body: AcquisitionMissionRunControl | None = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    return await _control_queued_run(
        run_id, ("paused",), "queued", body or AcquisitionMissionRunControl(), db
    )


@read_router.post("/{run_id}/cancel", response_model=AcquisitionMissionRunResponse)
async def cancel_acquisition_mission_run(
    run_id: uuid.UUID,
    body: AcquisitionMissionRunControl | None = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    run = await db.get(AcquisitionMissionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Acquisition Mission run not found")
    if run.lifecycle_status == "running":
        run.lifecycle_status = "cancel_requested"
        run.control_reason = (body or AcquisitionMissionRunControl()).reason
        run.checkpoints = [*run.checkpoints, "run:cancel_requested"]
        await db.commit()
        await db.refresh(run)
        return run
    return await _control_queued_run(
        run_id, ("queued", "scheduled"), "cancelled", body or AcquisitionMissionRunControl(), db
    )


@read_router.post(
    "/{run_id}/retry",
    response_model=AcquisitionMissionRunResponse,
    status_code=201,
)
async def retry_failed_acquisition_mission_run(
    run_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new queued run from a failed run without overwriting its audit record."""
    original = await db.get(AcquisitionMissionRun, run_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Acquisition Mission run not found")
    if original.lifecycle_status != "completed" or original.terminal_state != "failed":
        raise HTTPException(status_code=409, detail="Only completed failed runs can be retried")
    retry_run = AcquisitionMissionRun(
        mission_id=original.mission_id,
        source_config_version_id=original.source_config_version_id,
        replay_of_run_id=original.id,
        execution_mode=original.execution_mode,
        lifecycle_status="queued",
        input_snapshot=copy.deepcopy(original.input_snapshot),
        budgets=copy.deepcopy(original.budgets),
        raw_artifacts=[],
        parser_version=original.parser_version,
        context_completeness={
            "issue": False,
            "comments": False,
            "parent_context": False,
            "pagination_complete": False,
            "missing": ["not_collected"],
        },
        checkpoints=["run:retry_queued"],
        retry_count=0,
        terminal_state="not_started",
        failure_detail=None,
        transport_requests=0,
        network_requests=0,
        external_signal_ids=[],
    )
    db.add(retry_run)
    await db.commit()
    await db.refresh(retry_run)
    return retry_run


@read_router.post(
    "/{run_id}/execute",
    response_model=AcquisitionMissionRunResponse,
    status_code=202,
)
async def execute_queued_acquisition_mission_run(
    run_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Hand an explicitly approved run to a durable worker; do not collect in the API process."""
    run = await db.get(AcquisitionMissionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Acquisition Mission run not found")
    if run.lifecycle_status != "queued":
        raise HTTPException(
            status_code=409, detail=f"Run is {run.lifecycle_status}; expected queued"
        )

    run.lifecycle_status = "scheduled"
    run.checkpoints = [*run.checkpoints, "run:scheduled"]
    await db.commit()
    await db.refresh(run)
    return run


@read_router.get("/{run_id}", response_model=AcquisitionMissionRunResponse)
async def get_acquisition_mission_run(
    run_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    run = await db.get(AcquisitionMissionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Acquisition Mission run not found")
    return run
