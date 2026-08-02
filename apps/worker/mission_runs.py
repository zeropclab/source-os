"""Database-backed, leased execution for explicitly scheduled Acquisition Mission runs."""

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from packages.adapters.github_mission import (
    BoundedGitHubMissionTransport,
    ContextCompleteness,
    GitHubMissionAdapter,
    GitHubMissionResult,
    GitHubMissionTransport,
    SignalDraft,
)
from packages.storage.models.acquisition_mission import AcquisitionMission
from packages.storage.models.acquisition_mission_run import AcquisitionMissionRun
from packages.storage.models.acquisition_mission_run_signal import AcquisitionMissionRunSignal
from packages.storage.models.external_signal import ExternalSignal
from packages.storage.models.source import Source


def _timeout_result(timeout_seconds: int) -> GitHubMissionResult:
    return GitHubMissionResult(
        raw_artifacts=[],
        signals=[],
        context_completeness=ContextCompleteness(
            False, False, False, False, ("issue_page", "comments", "parent_context")
        ),
        checkpoints=["run:timeout"],
        retry_count=0,
        terminal_state="failed",
        failure_detail=f"Mission exceeded its {timeout_seconds} second time budget.",
    )


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
    signals = await db.scalars(
        select(ExternalSignal).where(
            ExternalSignal.lineage_key.in_([draft.lineage_key for draft in drafts])
        )
    )
    signal_by_lineage = {signal.lineage_key: signal for signal in signals}
    run.external_signal_ids = [str(signal_by_lineage[draft.lineage_key].id) for draft in drafts]
    await db.execute(
        insert(AcquisitionMissionRunSignal)
        .values(
            [
                {"run_id": run.id, "signal_id": signal_id, "ordinal": ordinal}
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


async def claim_next_mission_run(
    db: AsyncSession,
    *,
    worker_id: str,
    lease_seconds: int,
    now: datetime | None = None,
) -> AcquisitionMissionRun | None:
    """Claim one explicitly scheduled or expired run with a database lease."""
    current_time = now or datetime.now(UTC)
    run = await db.scalar(
        select(AcquisitionMissionRun)
        .where(
            or_(
                AcquisitionMissionRun.lifecycle_status == "scheduled",
                (
                    (AcquisitionMissionRun.lifecycle_status == "running")
                    & (AcquisitionMissionRun.lease_expires_at < current_time)
                ),
            )
        )
        .order_by(AcquisitionMissionRun.started_at.asc(), AcquisitionMissionRun.id.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if run is None:
        return None
    mission = await db.get(AcquisitionMission, run.mission_id)
    if mission is None:
        raise ValueError("Mission no longer exists")
    reclaimed = run.lifecycle_status == "running"
    run.lifecycle_status = "running"
    run.lease_owner = worker_id
    effective_lease_seconds = max(lease_seconds, (mission.time_budget_minutes * 60) + 60)
    run.lease_expires_at = current_time + timedelta(seconds=effective_lease_seconds)
    run.execution_attempt += 1
    run.checkpoints = [*run.checkpoints, "run:lease_reclaimed" if reclaimed else "run:leased"]
    await db.commit()
    await db.refresh(run)
    return run


async def execute_claimed_mission_run(
    db: AsyncSession,
    *,
    run_id,
    worker_id: str,
    fixture_transport: GitHubMissionTransport,
    live_transport: GitHubMissionTransport,
) -> AcquisitionMissionRun:
    """Collect only a run currently leased by this worker, then atomically finalize its assets."""
    run = await db.get(AcquisitionMissionRun, run_id)
    if (
        run is None
        or run.lifecycle_status not in {"running", "cancel_requested"}
        or run.lease_owner != worker_id
    ):
        raise ValueError("Mission run is not leased by this worker")
    mission = await db.scalar(
        select(AcquisitionMission)
        .options(joinedload(AcquisitionMission.source_config_version))
        .where(AcquisitionMission.id == run.mission_id)
    )
    if mission is None or mission.source_config_version is None:
        raise ValueError("Mission no longer has a pinned source configuration")
    source = await db.get(Source, mission.source_id)
    if source is None:
        raise ValueError("Mission source no longer exists")

    config = mission.source_config_version
    selected_transport = live_transport if run.execution_mode == "live" else fixture_transport
    transport = BoundedGitHubMissionTransport(
        selected_transport, request_limit=config.request_policy["request_limit"]
    )
    timeout_seconds = config.request_policy["timeout_seconds"]
    try:
        async with asyncio.timeout(timeout_seconds):
            result = await GitHubMissionAdapter().collect(
                source.url, config, transport, item_limit=mission.item_limit
            )
    except TimeoutError:
        result = _timeout_result(timeout_seconds)
    except Exception as error:
        run.lifecycle_status = "completed"
        run.terminal_state = "failed"
        run.failure_detail = f"Worker collection failed: {error}"
        run.checkpoints = [*run.checkpoints, "run:worker_error"]
        run.lease_owner = None
        run.lease_expires_at = None
        run.completed_at = func.now()
        await db.commit()
        await db.refresh(run)
        return run

    await db.refresh(run)
    if run.lifecycle_status == "cancel_requested":
        run.raw_artifacts = result.raw_artifacts
        run.context_completeness = result.context_completeness.as_dict()
        run.checkpoints = [*run.checkpoints, *result.checkpoints, "run:cancelled_at_checkpoint"]
        run.retry_count = result.retry_count
        run.transport_requests = transport.transport_requests
        run.network_requests = transport.network_requests
        run.lifecycle_status = "cancelled"
        run.terminal_state = "cancelled"
        run.failure_detail = "Cancellation took effect after the current collection checkpoint."
        run.lease_owner = None
        run.lease_expires_at = None
        run.completed_at = func.now()
        await db.commit()
        await db.refresh(run)
        return run

    run.raw_artifacts = result.raw_artifacts
    run.context_completeness = result.context_completeness.as_dict()
    run.checkpoints = [*run.checkpoints, *result.checkpoints]
    run.retry_count = result.retry_count
    run.terminal_state = result.terminal_state
    run.failure_detail = result.failure_detail
    run.transport_requests = transport.transport_requests
    run.network_requests = transport.network_requests
    run.lifecycle_status = "completed"
    run.lease_owner = None
    run.lease_expires_at = None
    run.completed_at = func.now()
    await _persist_signal_drafts(db, run, result.signals)
    await db.commit()
    await db.refresh(run)
    return run


async def process_one_mission_run(
    db: AsyncSession,
    *,
    worker_id: str,
    lease_seconds: int,
    fixture_transport: GitHubMissionTransport,
    live_transport: GitHubMissionTransport,
) -> AcquisitionMissionRun | None:
    """Claim and execute at most one scheduled run; safe to call in a worker polling loop."""
    run = await claim_next_mission_run(db, worker_id=worker_id, lease_seconds=lease_seconds)
    if run is None:
        return None
    return await execute_claimed_mission_run(
        db,
        run_id=run.id,
        worker_id=worker_id,
        fixture_transport=fixture_transport,
        live_transport=live_transport,
    )
