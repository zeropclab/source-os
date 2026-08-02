"""Bounded GitHub transports for live, fixture, and raw-artifact execution."""

from dataclasses import dataclass
from typing import Protocol

import httpx


@dataclass(frozen=True)
class GitHubPage:
    items: list[dict]
    page: int
    has_next_page: bool


class GitHubMissionTransport(Protocol):
    transport_requests: int

    @property
    def network_requests(self) -> int: ...

    async def list_issues(
        self, owner: str, repo: str, query_terms: list[str], page: int = 1
    ) -> GitHubPage: ...

    async def list_issue_comments(self, owner: str, repo: str, issue_number: int) -> GitHubPage: ...


class GitHubRateLimitError(RuntimeError):
    pass


class GitHubRequestBudgetExceededError(RuntimeError):
    pass


class GitHubTransportError(RuntimeError):
    def __init__(self, detail: str, *, status_code: int | None = None):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


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

    async def list_issues(
        self, owner: str, repo: str, query_terms: list[str], page: int = 1
    ) -> GitHubPage:
        self._consume_request()
        if page == 1:
            return await self._transport.list_issues(owner, repo, query_terms)
        return await self._transport.list_issues(owner, repo, query_terms, page=page)

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
        try:
            async with httpx.AsyncClient(
                base_url=self._api_base_url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "SourceOS-public-source-adapter",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            ) as client:
                response = await client.get(path, params=params)
        except httpx.RequestError as exc:
            raise GitHubTransportError("GitHub network request failed.") from exc
        if response.status_code == 429 or (
            response.status_code == 403 and response.headers.get("x-ratelimit-remaining") == "0"
        ):
            raise GitHubRateLimitError
        if response.is_error:
            raise GitHubTransportError(
                f"GitHub returned HTTP {response.status_code}.",
                status_code=response.status_code,
            )
        return response

    @staticmethod
    def _page(response: httpx.Response, items: list[dict], page: int) -> GitHubPage:
        return GitHubPage(
            items=items,
            page=page,
            has_next_page='rel="next"' in response.headers.get("link", ""),
        )

    async def list_issues(
        self, owner: str, repo: str, query_terms: list[str], page: int = 1
    ) -> GitHubPage:
        response = await self._get(
            f"/repos/{owner}/{repo}/issues",
            {"state": "all", "per_page": 100, "page": page},
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise GitHubTransportError("GitHub issues response was not valid JSON.") from exc
        if not isinstance(payload, list):
            raise GitHubTransportError("GitHub issues response must be a list.")
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
        return self._page(response, issues, page)

    async def list_issue_comments(self, owner: str, repo: str, issue_number: int) -> GitHubPage:
        response = await self._get(
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            {"per_page": 100, "page": 1},
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise GitHubTransportError(
                "GitHub issue comments response was not valid JSON."
            ) from exc
        if not isinstance(payload, list):
            raise GitHubTransportError("GitHub issue comments response must be a list.")
        return self._page(response, [item for item in payload if isinstance(item, dict)], 1)


class GitHubArtifactReplayTransport:
    """Read one prior run's raw artifacts without transport or network I/O."""

    transport_requests = 0
    network_requests = 0

    def __init__(self, raw_artifacts: list[dict]):
        self._raw_artifacts = raw_artifacts

    async def list_issues(
        self, owner: str, repo: str, query_terms: list[str], page: int = 1
    ) -> GitHubPage:
        page_artifact = next(
            (
                item
                for item in self._raw_artifacts
                if item.get("kind") == "issue_page" and item.get("raw", {}).get("page", 1) == page
            ),
            None,
        )
        if page_artifact is not None:
            raw = page_artifact["raw"]
            return GitHubPage(
                items=raw.get("items", []),
                page=raw.get("page", 1),
                has_next_page=raw.get("has_next_page", False),
            )
        issues = [item["raw"] for item in self._raw_artifacts if item.get("kind") == "issue"]
        return GitHubPage(items=issues if page == 1 else [], page=page, has_next_page=False)

    async def list_issue_comments(self, owner: str, repo: str, issue_number: int) -> GitHubPage:
        issue_key = f"github:{owner}/{repo}:issue:{issue_number}"
        page_artifact = next(
            (
                item
                for item in self._raw_artifacts
                if item.get("kind") == "comment_page"
                and item.get("parent_artifact_key") == issue_key
            ),
            None,
        )
        if page_artifact is not None:
            raw = page_artifact["raw"]
            return GitHubPage(
                items=raw.get("items", []),
                page=raw.get("page", 1),
                has_next_page=raw.get("has_next_page", False),
            )
        comments = [
            item["raw"]
            for item in self._raw_artifacts
            if item.get("kind") == "comment" and item.get("parent_artifact_key") == issue_key
        ]
        return GitHubPage(items=comments, page=1, has_next_page=False)
