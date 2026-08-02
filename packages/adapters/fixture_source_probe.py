"""Deterministic reference probe adapter with no live network dependency."""

from packages.adapters.source_probe import (
    AccessState,
    ProbeExecution,
    ProbeRequest,
    ProbeResponse,
    ProbeResult,
    UnsupportedSourceProbeAdapter,
)
from packages.storage.models.source import Source
from packages.storage.models.source_config_version import SourceConfigVersion


class FixtureProbeTransport:
    """Execute deterministic fixture requests without any network access."""

    async def execute(self, request: ProbeRequest) -> ProbeResponse:
        if not request.target.startswith("fixture://"):
            raise ValueError("Fixture transport refuses non-fixture targets")
        return ProbeResponse(payload={"target": request.target})


class FixtureSourceProbeAdapter:
    async def probe(
        self,
        source: Source,
        config: SourceConfigVersion,
        *,
        execution: ProbeExecution,
    ) -> ProbeResult:
        await execution.request(ProbeRequest(target=f"fixture://{source.source_type}"))
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
        access_failures: dict[str, tuple[AccessState, str]] = {
            "credentialed": (
                "credentialed",
                "Credentials are required before source capabilities can be verified.",
            ),
            "subscription_gated": (
                "subscription",
                "A subscription is required before source capabilities can be verified.",
            ),
            "blocked": (
                "blocked",
                "The source blocked the probe before capabilities could be verified.",
            ),
        }
        if source.source_type in access_failures:
            access_state, risk = access_failures[source.source_type]
            return ProbeResult(
                status="failed",
                access_state=access_state,
                sample=None,
                pagination_supported=None,
                replies_supported=None,
                context_risks=[risk],
                outcome_detail=source.source_type,
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
