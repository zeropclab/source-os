"""Runtime-controlled adapter boundary for bounded source-capability probes."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal, Protocol, TypeVar

from packages.storage.models.source import Source
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
    pagination_supported: bool | None
    replies_supported: bool | None
    context_risks: list[str]
    outcome_detail: str | None = None


class ProbeRequestBudgetExceededError(RuntimeError):
    pass


RequestResult = TypeVar("RequestResult")


@dataclass
class ProbeExecution:
    request_limit: int
    time_limit_seconds: int
    _consumed_requests: int = 0

    @property
    def consumed_requests(self) -> int:
        return self._consumed_requests

    async def request(self, operation: Callable[[], Awaitable[RequestResult]]) -> RequestResult:
        """Run one external request through the runtime-owned budget gate."""
        if self._consumed_requests >= self.request_limit:
            raise ProbeRequestBudgetExceededError
        self._consumed_requests += 1
        return await operation()


class SourceProbeAdapter(Protocol):
    async def probe(
        self,
        source: Source,
        config: SourceConfigVersion,
        *,
        execution: ProbeExecution,
    ) -> ProbeResult: ...


class UnsupportedSourceProbeAdapter:
    """Safe default until a platform-specific adapter is registered."""

    async def probe(
        self,
        source: Source,
        config: SourceConfigVersion,
        *,
        execution: ProbeExecution,
    ) -> ProbeResult:
        return ProbeResult(
            status="failed",
            access_state="unsupported",
            sample=None,
            pagination_supported=None,
            replies_supported=None,
            context_risks=["No probe adapter is registered for this source."],
            outcome_detail="unsupported_adapter",
        )
