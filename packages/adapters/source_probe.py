"""Adapter boundary for bounded source-capability probes."""

from dataclasses import dataclass
from typing import Literal, Protocol

from packages.storage.models.source_config_version import SourceConfigVersion

ProbeStatus = Literal["succeeded", "empty", "failed"]
AccessState = Literal[
    "public", "credentialed", "subscription", "rate_limited", "blocked", "unsupported"
]


@dataclass(frozen=True)
class ProbeResult:
    status: ProbeStatus
    access_state: AccessState
    sample: dict[str, str] | None
    pagination_supported: bool
    replies_supported: bool
    context_risks: list[str]
    outcome_detail: str | None = None


class ProbeRequestBudgetExceededError(RuntimeError):
    pass


@dataclass
class ProbeBudget:
    request_limit: int
    time_limit_seconds: int
    consumed_requests: int = 0

    def consume_request(self) -> None:
        if self.consumed_requests >= self.request_limit:
            raise ProbeRequestBudgetExceededError
        self.consumed_requests += 1


class SourceProbeAdapter(Protocol):
    async def probe(
        self,
        config: SourceConfigVersion,
        *,
        budget: ProbeBudget,
    ) -> ProbeResult: ...


class UnsupportedSourceProbeAdapter:
    """Safe default until a platform-specific adapter is registered."""

    async def probe(
        self,
        config: SourceConfigVersion,
        *,
        budget: ProbeBudget,
    ) -> ProbeResult:
        return ProbeResult(
            status="failed",
            access_state="unsupported",
            sample=None,
            pagination_supported=False,
            replies_supported=False,
            context_risks=["No probe adapter is registered for this source."],
            outcome_detail="unsupported_adapter",
        )


class FixtureSourceProbeAdapter:
    """Deterministic adapter used to prove orchestration without live network access."""

    def __init__(self, scenario: str):
        self.scenario = scenario

    async def probe(
        self,
        config: SourceConfigVersion,
        *,
        budget: ProbeBudget,
    ) -> ProbeResult:
        if self.scenario == "accessible_with_context":
            budget.consume_request()
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
        if self.scenario == "empty_result":
            budget.consume_request()
            return ProbeResult(
                status="empty",
                access_state="public",
                sample=None,
                pagination_supported=True,
                replies_supported=True,
                context_risks=[],
                outcome_detail="No matching material was returned.",
            )
        if self.scenario == "rate_limited":
            budget.consume_request()
            return ProbeResult(
                status="failed",
                access_state="rate_limited",
                sample=None,
                pagination_supported=False,
                replies_supported=False,
                context_risks=[
                    "Pagination and reply context could not be verified because the source "
                    "rate-limited the probe."
                ],
                outcome_detail="rate_limited",
            )
        raise ValueError(f"Unknown fixture probe scenario: {self.scenario}")
