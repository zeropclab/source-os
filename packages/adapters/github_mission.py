"""Reference GitHub mission adapter and deterministic transport fixtures."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from urllib.parse import urlparse

import httpx

from packages.storage.models.acquisition_mission import AcquisitionMission
from packages.storage.models.source import Source
from packages.storage.models.source_config_version import SourceConfigVersion


@dataclass(frozen=True)
class GitHubPage:
    items: list[dict]
    page: int
    has_next_page: bool


class GitHubMissionTransport(Protocol):
    transport_requests: int
    network_requests: int

    async def list_issues(self, owner: str, repo: str, query_terms: list[str]) -> GitHubPage: ...

    async def list_issue_comments(self, owner: str, repo: str, issue_number: int) -> GitHubPage: ...


class GitHubRateLimitError(RuntimeError):
    pass


class GitHubRequestBudgetExceededError(RuntimeError):
    pass


class BoundedGitHubMissionTransport:
    """Runtime-owned gate that accounts for every adapter transport request."""

    def __init__(self, transport: GitHubMissionTransport, request_limit: int):
        self._transport = transport
        self._request_limit = request_limit
        self.transport_requests = 0

    @property
    def network_requests(self) -> int:
        return self._transport.network_requests

    def _consume_request(self) -> None:
        if self.transport_requests >= self._request_limit:
            raise GitHubRequestBudgetExceededError
        self.transport_requests += 1

    async def list_issues(self, owner: str, repo: str, query_terms: list[str]) -> GitHubPage:
        self._consume_request()
        return await self._transport.list_issues(owner, repo, query_terms)

    async def list_issue_comments(self, owner: str, repo: str, issue_number: int) -> GitHubPage:
        self._consume_request()
        return await self._transport.list_issue_comments(owner, repo, issue_number)


class GitHubFixtureTransport:
    """No-network transport for deterministic adapter execution."""

    def __init__(self, scenario: str):
        self.scenario = scenario
        self.transport_requests = 0
        self.network_requests = 0

    async def list_issues(self, owner: str, repo: str, query_terms: list[str]) -> GitHubPage:
        self.transport_requests += 1
        if self.scenario == "rate_limited":
            raise GitHubRateLimitError
        if self.scenario not in {
            "issue_with_context",
            "missing_parent",
            "empty",
            "parsing_failure",
        }:
            raise ValueError(f"Unknown GitHub fixture scenario: {self.scenario}")
        if self.scenario == "empty":
            return GitHubPage(items=[], page=1, has_next_page=False)
        if self.scenario == "parsing_failure":
            return GitHubPage(
                items=[{"title": "Malformed fixture without an issue number"}],
                page=1,
                has_next_page=False,
            )
        parent_available = self.scenario == "issue_with_context"
        return GitHubPage(
            items=[
                {
                    "number": 42,
                    "title": "Cross-border payout reconciliation takes hours",
                    "body": (
                        "I spend three hours every week matching payout rows to invoices."
                        if parent_available
                        else None
                    ),
                    "parent_available": parent_available,
                    "html_url": f"https://github.com/{owner}/{repo}/issues/42",
                    "created_at": "2026-07-30T10:00:00+00:00",
                }
            ],
            page=1,
            has_next_page=False,
        )

    async def list_issue_comments(self, owner: str, repo: str, issue_number: int) -> GitHubPage:
        self.transport_requests += 1
        return GitHubPage(
            items=[
                {
                    "id": 4201,
                    "body": "We export two dashboards and match rows manually before bookkeeping.",
                    "html_url": (
                        f"https://github.com/{owner}/{repo}/issues/{issue_number}#issuecomment-4201"
                    ),
                    "created_at": "2026-07-30T11:00:00+00:00",
                }
            ],
            page=1,
            has_next_page=False,
        )


class GitHubPublicTransport:
    """Unauthenticated GitHub REST transport for public repositories."""

    def __init__(self, *, api_base_url: str = "https://api.github.com"):
        self._api_base_url = api_base_url.rstrip("/")
        self.transport_requests = 0
        self.network_requests = 0

    async def _get(self, path: str, params: dict[str, str | int]) -> httpx.Response:
        self.transport_requests += 1
        self.network_requests += 1
        async with httpx.AsyncClient(
            base_url=self._api_base_url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "SourceOS-public-source-adapter",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        ) as client:
            response = await client.get(path, params=params)
        if response.status_code == 429 or (
            response.status_code == 403 and response.headers.get("x-ratelimit-remaining") == "0"
        ):
            raise GitHubRateLimitError
        response.raise_for_status()
        return response

    @staticmethod
    def _page(response: httpx.Response, items: list[dict]) -> GitHubPage:
        return GitHubPage(
            items=items,
            page=1,
            has_next_page='rel="next"' in response.headers.get("link", ""),
        )

    async def list_issues(self, owner: str, repo: str, query_terms: list[str]) -> GitHubPage:
        response = await self._get(
            f"/repos/{owner}/{repo}/issues",
            {"state": "all", "per_page": 100, "page": 1},
        )
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("GitHub issues response must be a list")
        issues = [item for item in payload if isinstance(item, dict) and "pull_request" not in item]
        normalized_terms = [term.casefold() for term in query_terms if term.strip()]
        if normalized_terms:
            issues = [
                issue
                for issue in issues
                if any(
                    term in f"{issue.get('title', '')}\n{issue.get('body') or ''}".casefold()
                    for term in normalized_terms
                )
            ]
        return self._page(response, issues)

    async def list_issue_comments(self, owner: str, repo: str, issue_number: int) -> GitHubPage:
        response = await self._get(
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            {"per_page": 100, "page": 1},
        )
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("GitHub issue comments response must be a list")
        return self._page(response, [item for item in payload if isinstance(item, dict)])


@dataclass(frozen=True)
class SignalDraft:
    lineage_key: str
    raw_artifact_key: str
    source_label: str
    source_uri: str
    original_material: str
    observed_at: datetime
    observation: str
    parent_context_available: bool
    context_snapshot: dict


@dataclass(frozen=True)
class GitHubMissionResult:
    raw_artifacts: list[dict]
    signals: list[SignalDraft]
    context_completeness: dict
    checkpoints: list[str]
    retry_count: int
    terminal_state: str
    failure_detail: str | None


def _repository_coordinates(source: Source) -> tuple[str, str]:
    parsed = urlparse(source.url)
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.hostname != "github.com" or len(parts) < 2:
        raise ValueError("GitHub source URL must identify an owner and repository")
    return parts[0], parts[1]


def _evidence_observation(kind: str, *parts: str | None) -> str:
    material = " ".join(" ".join(part.split()) for part in parts if part).strip()
    return f"GitHub {kind} states: {material[:500]}"


class GitHubMissionAdapter:
    async def collect(
        self,
        source: Source,
        config: SourceConfigVersion,
        mission: AcquisitionMission,
        transport: GitHubMissionTransport,
    ) -> GitHubMissionResult:
        owner, repo = _repository_coordinates(source)
        retry_limit = config.request_policy.get("retry_limit", 0)
        rate_limit_artifacts = []
        rate_limit_checkpoints = []
        issue_page = None
        for attempt in range(1, retry_limit + 2):
            try:
                issue_page = await transport.list_issues(
                    owner,
                    repo,
                    config.query_scope["query_terms"],
                )
                break
            except GitHubRateLimitError:
                rate_limit_checkpoints.append(f"issues:attempt:{attempt}:rate_limited")
                rate_limit_artifacts.append(
                    {
                        "artifact_key": f"github:{owner}/{repo}:rate-limit:attempt:{attempt}",
                        "kind": "transport_failure",
                        "source_uri": f"https://api.github.com/repos/{owner}/{repo}/issues",
                        "raw": {"status": 429, "attempt": attempt},
                    }
                )
        if issue_page is None:
            return GitHubMissionResult(
                raw_artifacts=rate_limit_artifacts,
                signals=[],
                context_completeness={
                    "issue": False,
                    "comments": False,
                    "parent_context": False,
                    "pagination_complete": False,
                    "missing": ["issue_page", "comments", "parent_context"],
                },
                checkpoints=rate_limit_checkpoints,
                retry_count=retry_limit,
                terminal_state="failed",
                failure_detail=f"GitHub rate limit persisted after {retry_limit} retry.",
            )
        if not issue_page.items:
            page_key = f"github:{owner}/{repo}:issues:page:{issue_page.page}"
            return GitHubMissionResult(
                raw_artifacts=[
                    {
                        "artifact_key": page_key,
                        "kind": "issue_page",
                        "source_uri": (
                            f"https://github.com/{owner}/{repo}/issues?page={issue_page.page}"
                        ),
                        "raw": {
                            "items": [],
                            "has_next_page": issue_page.has_next_page,
                        },
                    }
                ],
                signals=[],
                context_completeness={
                    "issue": False,
                    "comments": False,
                    "parent_context": False,
                    "pagination_complete": not issue_page.has_next_page,
                    "missing": ["matching_issues"],
                },
                checkpoints=[f"issues:page:{issue_page.page}"],
                retry_count=0,
                terminal_state="empty",
                failure_detail="No GitHub issues matched the pinned query.",
            )
        issue_page_artifact = {
            "artifact_key": f"github:{owner}/{repo}:issues:page:{issue_page.page}",
            "kind": "issue_page",
            "source_uri": f"https://github.com/{owner}/{repo}/issues?page={issue_page.page}",
            "raw": {
                "items": issue_page.items,
                "has_next_page": issue_page.has_next_page,
            },
        }
        issue = issue_page.items[0]
        required_fields = ["number", "title", "body", "html_url", "created_at"]
        missing_field = next((field for field in required_fields if field not in issue), None)
        if missing_field is not None:
            return GitHubMissionResult(
                raw_artifacts=[issue_page_artifact],
                signals=[],
                context_completeness={
                    "issue": False,
                    "comments": False,
                    "parent_context": False,
                    "pagination_complete": not issue_page.has_next_page,
                    "missing": ["parser_output"],
                },
                checkpoints=[
                    f"issues:page:{issue_page.page}",
                    f"issues:page:{issue_page.page}:parse_failed",
                ],
                retry_count=0,
                terminal_state="failed",
                failure_detail=(
                    f"GitHub issue parser could not read required field: {missing_field}."
                ),
            )
        issue_key = f"github:{owner}/{repo}:issue:{issue['number']}"
        issue_artifact = {
            "artifact_key": issue_key,
            "kind": "issue",
            "source_uri": issue["html_url"],
            "raw": issue,
        }
        parent_available = issue.get("parent_available", True)
        issue_context = {
            "issue_number": issue["number"],
            "pagination_complete": False,
        }
        if parent_available:
            issue_context["issue_title"] = issue["title"]
            issue_signal = SignalDraft(
                lineage_key=issue_key,
                raw_artifact_key=issue_key,
                source_label=f"GitHub {owner}/{repo} issue #{issue['number']}",
                source_uri=issue["html_url"],
                original_material=(
                    f"{issue['title']}\n\n{issue['body']}" if issue["body"] else issue["title"]
                ),
                observed_at=datetime.fromisoformat(issue["created_at"]),
                observation=_evidence_observation("issue", issue["title"], issue["body"]),
                parent_context_available=True,
                context_snapshot=issue_context,
            )
        else:
            issue_context["missing"] = ["issue_parent"]
            issue_signal = None
        try:
            comment_page = await transport.list_issue_comments(owner, repo, issue["number"])
        except GitHubRequestBudgetExceededError:
            return GitHubMissionResult(
                raw_artifacts=[issue_artifact],
                signals=[] if issue_signal is None else [issue_signal],
                context_completeness={
                    "issue": parent_available,
                    "comments": False,
                    "parent_context": parent_available,
                    "pagination_complete": False,
                    "missing": ["comments"],
                },
                checkpoints=[
                    f"issues:page:{issue_page.page}",
                    f"issue:{issue['number']}:comments:budget_exhausted",
                ],
                retry_count=0,
                terminal_state="partial",
                failure_detail=("Request budget exhausted before comment context was collected."),
            )
        if not comment_page.items:
            pagination_complete = not issue_page.has_next_page and not comment_page.has_next_page
            issue_context["pagination_complete"] = pagination_complete
            comment_page_key = (
                f"github:{owner}/{repo}:issue:{issue['number']}:comments:page:{comment_page.page}"
            )
            return GitHubMissionResult(
                raw_artifacts=[
                    issue_artifact,
                    {
                        "artifact_key": comment_page_key,
                        "kind": "comment_page",
                        "source_uri": (
                            f"https://github.com/{owner}/{repo}/issues/"
                            f"{issue['number']}?page={comment_page.page}"
                        ),
                        "raw": {
                            "items": [],
                            "has_next_page": comment_page.has_next_page,
                        },
                        "parent_artifact_key": issue_key,
                    },
                ],
                signals=[] if issue_signal is None else [issue_signal],
                context_completeness={
                    "issue": parent_available,
                    "comments": True,
                    "parent_context": parent_available,
                    "pagination_complete": pagination_complete,
                    "missing": [] if parent_available else ["issue_parent"],
                },
                checkpoints=[
                    f"issues:page:{issue_page.page}",
                    f"issue:{issue['number']}:comments:page:{comment_page.page}",
                ],
                retry_count=0,
                terminal_state="succeeded" if parent_available else "partial",
                failure_detail=(
                    None if parent_available else "Parent issue context was unavailable."
                ),
            )
        comment = comment_page.items[0]
        comment_key = f"github:{owner}/{repo}:comment:{comment['id']}"
        pagination_complete = not issue_page.has_next_page and not comment_page.has_next_page
        issue_context["pagination_complete"] = pagination_complete
        if parent_available:
            issue_context["issue_title"] = issue["title"]
        else:
            issue_context["missing"] = ["issue_parent"]
        raw_artifacts = [
            issue_artifact,
            {
                "artifact_key": comment_key,
                "kind": "comment",
                "source_uri": comment["html_url"],
                "raw": comment,
                "parent_artifact_key": issue_key,
            },
        ]
        signals = []
        if issue_signal is not None:
            signals.append(issue_signal)
        signals.append(
            SignalDraft(
                lineage_key=comment_key,
                raw_artifact_key=comment_key,
                source_label=f"GitHub {owner}/{repo} issue #{issue['number']} comment",
                source_uri=comment["html_url"],
                original_material=comment["body"],
                observed_at=datetime.fromisoformat(comment["created_at"]),
                observation=_evidence_observation("comment", comment["body"]),
                parent_context_available=parent_available,
                context_snapshot=issue_context,
            )
        )
        return GitHubMissionResult(
            raw_artifacts=raw_artifacts,
            signals=signals,
            context_completeness={
                "issue": parent_available,
                "comments": True,
                "parent_context": parent_available,
                "pagination_complete": pagination_complete,
                "missing": [] if parent_available else ["issue_parent"],
            },
            checkpoints=["issues:page:1", f"issue:{issue['number']}:comments:page:1"],
            retry_count=0,
            terminal_state="succeeded" if parent_available else "partial",
            failure_detail=(None if parent_available else "Parent issue context was unavailable."),
        )
