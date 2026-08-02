"""Execute pinned Acquisition Missions and retrieve their lineage."""

import asyncio
import copy
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
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
    AcquisitionMissionRunCreate,
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
    return mission


def _input_snapshot(mission: AcquisitionMission) -> dict:
    mission_data = AcquisitionMissionResponse.model_validate(mission).model_dump(mode="json")
    config_data = mission_data.pop("source_config_version")
    return {"mission": mission_data, "source_config_version": config_data}


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
                source,
                config,
                mission,
                bounded_transport,
            )
    except TimeoutError:
        result = GitHubMissionResult(
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
    run = AcquisitionMissionRun(
        mission_id=mission.id,
        source_config_version_id=config.id,
        replay_of_run_id=None,
        execution_mode=body.execution_mode,
        input_snapshot=_input_snapshot(mission),
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
    )
    db.add(run)
    await db.flush()
    await _persist_signal_drafts(db, run, result.signals)
    await db.commit()
    await db.refresh(run)
    return run


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
    source = await db.get(Source, mission.source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    replay_result = await GitHubMissionAdapter().collect(
        source,
        mission.source_config_version,
        mission,
        GitHubArtifactReplayTransport(copy.deepcopy(original.raw_artifacts)),
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
        input_snapshot=copy.deepcopy(original.input_snapshot),
        budgets=copy.deepcopy(original.budgets),
        raw_artifacts=copy.deepcopy(original.raw_artifacts),
        parser_version=original.parser_version,
        context_completeness=replay_result.context_completeness.as_dict(),
        checkpoints=[*replay_result.checkpoints, "replay:lineage_verified"],
        retry_count=replay_result.retry_count,
        terminal_state=(replay_result.terminal_state if lineage_verified else "failed"),
        failure_detail=(
            replay_result.failure_detail
            if lineage_verified
            else "Replay lineage diverged from the original mission run."
        ),
        transport_requests=0,
        network_requests=0,
        external_signal_ids=[],
    )
    db.add(replay)
    await db.flush()
    if lineage_verified:
        await _persist_signal_drafts(db, replay, replay_result.signals)
    await db.commit()
    await db.refresh(replay)
    return replay


@read_router.get("/{run_id}", response_model=AcquisitionMissionRunResponse)
async def get_acquisition_mission_run(
    run_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    run = await db.get(AcquisitionMissionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Acquisition Mission run not found")
    return run
