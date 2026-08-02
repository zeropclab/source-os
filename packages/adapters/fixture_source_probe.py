"""Deterministic reference probe adapter with no live network dependency."""

from packages.adapters.source_probe import (
    ProbeExecution,
    ProbeResult,
    UnsupportedSourceProbeAdapter,
)
from packages.storage.models.source import Source
from packages.storage.models.source_config_version import SourceConfigVersion


async def _fixture_request() -> None:
    return None


class FixtureSourceProbeAdapter:
    async def probe(
        self,
        source: Source,
        config: SourceConfigVersion,
        *,
        execution: ProbeExecution,
    ) -> ProbeResult:
        await execution.request(_fixture_request)
        if source.source_type == "accessible_with_context":
            return ProbeResult(
                status="succeeded",
                access_state="public",
                sample={
                    "title": "Users need reply context",
                    "body": "The top-level comment is ambiguous without its parent discussion.",
                },
                pagination_supported=True,
                replies_supported=True,
                context_risks=[],
            )
        if source.source_type == "empty_result":
            return ProbeResult(
                status="empty",
                access_state="public",
                sample=None,
                pagination_supported=True,
                replies_supported=True,
                context_risks=[],
                outcome_detail="No matching material was returned.",
            )
        if source.source_type == "rate_limited":
            return ProbeResult(
                status="failed",
                access_state="rate_limited",
                sample=None,
                pagination_supported=None,
                replies_supported=None,
                context_risks=[
                    "Pagination and reply context could not be verified because the source "
                    "rate-limited the probe."
                ],
                outcome_detail="rate_limited",
            )
        return await UnsupportedSourceProbeAdapter().probe(
            source,
            config,
            execution=execution,
        )


class DispatchingSourceProbeAdapter:
    """Select an explicit platform adapter without pretending unsupported sources work."""

    async def probe(
        self,
        source: Source,
        config: SourceConfigVersion,
        *,
        execution: ProbeExecution,
    ) -> ProbeResult:
        if source.platform == "fixture":
            return await FixtureSourceProbeAdapter().probe(
                source,
                config,
                execution=execution,
            )
        return await UnsupportedSourceProbeAdapter().probe(
            source,
            config,
            execution=execution,
        )
