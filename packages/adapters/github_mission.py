"""Parse bounded GitHub pages into raw artifacts and traceable evidence signals."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from urllib.parse import urlparse

from packages.adapters.github_transport import (
    BoundedGitHubMissionTransport,
    GitHubArtifactReplayTransport,
    GitHubFixtureTransport,
    GitHubMissionTransport,
    GitHubPage,
    GitHubPublicTransport,
    GitHubRateLimitError,
    GitHubRequestBudgetExceededError,
    GitHubTransportError,
)
from packages.storage.models.source_config_version import SourceConfigVersion

__all__ = [
    "BoundedGitHubMissionTransport",
    "ContextCompleteness",
    "GitHubArtifactReplayTransport",
    "GitHubFixtureTransport",
    "GitHubMissionAdapter",
    "GitHubMissionResult",
    "GitHubMissionTransport",
    "GitHubPage",
    "GitHubPublicTransport",
    "GitHubRateLimitError",
    "GitHubRequestBudgetExceededError",
    "GitHubTransportError",
    "SignalDraft",
]


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
class ContextCompleteness:
    issue: bool
    comments: bool
    parent_context: bool
    pagination_complete: bool
    missing: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "issue": self.issue,
            "comments": self.comments,
            "parent_context": self.parent_context,
            "pagination_complete": self.pagination_complete,
            "missing": list(self.missing),
        }


@dataclass(frozen=True)
class GitHubMissionResult:
    raw_artifacts: list[dict]
    signals: list[SignalDraft]
    context_completeness: ContextCompleteness
    checkpoints: list[str]
    retry_count: int
    terminal_state: str
    failure_detail: str | None


@dataclass(frozen=True)
class PageFetchOutcome:
    page: GitHubPage | None
    raw_artifacts: list[dict]
    checkpoints: list[str]
    retry_count: int
    error_kind: str | None = None
    error_detail: str | None = None


def _repository_coordinates(source_url: str) -> tuple[str, str]:
    parsed = urlparse(source_url)
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.hostname != "github.com" or len(parts) < 2:
        raise ValueError("GitHub source URL must identify an owner and repository")
    return parts[0], parts[1]


def _evidence_observation(kind: str, *parts: str | None) -> str:
    material = " ".join(" ".join(part.split()) for part in parts if part).strip()
    return f"GitHub {kind} states: {material[:500]}"


def _transport_failure_artifact(
    *, owner: str, repo: str, stage: str, attempt: int, status: int | None, detail: str
) -> dict:
    return {
        "artifact_key": f"github:{owner}/{repo}:{stage}:failure:attempt:{attempt}",
        "kind": "transport_failure",
        "source_uri": f"https://api.github.com/repos/{owner}/{repo}/issues",
        "raw": {"status": status, "attempt": attempt, "detail": detail},
    }


async def _fetch_page(
    call: Callable[[], Awaitable[GitHubPage]],
    *,
    owner: str,
    repo: str,
    stage: str,
    retry_limit: int,
) -> PageFetchOutcome:
    artifacts: list[dict] = []
    checkpoints: list[str] = []
    for attempt in range(1, retry_limit + 2):
        try:
            return PageFetchOutcome(await call(), artifacts, checkpoints, attempt - 1)
        except GitHubRateLimitError:
            checkpoints.append(f"{stage}:attempt:{attempt}:rate_limited")
            artifacts.append(
                _transport_failure_artifact(
                    owner=owner,
                    repo=repo,
                    stage=stage,
                    attempt=attempt,
                    status=429,
                    detail="rate_limited",
                )
            )
        except GitHubRequestBudgetExceededError:
            checkpoint = (
                f"{stage}:attempt:{attempt}:budget_exhausted"
                if stage == "issues"
                else f"{stage}:budget_exhausted"
            )
            checkpoints.append(checkpoint)
            return PageFetchOutcome(
                None,
                artifacts,
                checkpoints,
                max(0, attempt - 1),
                "budget_exhausted",
            )
        except GitHubTransportError as exc:
            checkpoints.append(f"{stage}:attempt:{attempt}:transport_failed")
            artifacts.append(
                _transport_failure_artifact(
                    owner=owner,
                    repo=repo,
                    stage=stage,
                    attempt=attempt,
                    status=exc.status_code,
                    detail=exc.detail,
                )
            )
            return PageFetchOutcome(
                None,
                artifacts,
                checkpoints,
                max(0, attempt - 1),
                "transport_failed",
                exc.detail,
            )
    return PageFetchOutcome(None, artifacts, checkpoints, retry_limit, "rate_limited")


def _issue_page_artifact(owner: str, repo: str, page: GitHubPage) -> dict:
    return {
        "artifact_key": f"github:{owner}/{repo}:issues:page:{page.page}",
        "kind": "issue_page",
        "source_uri": f"https://github.com/{owner}/{repo}/issues?page={page.page}",
        "raw": {
            "items": page.items,
            "page": page.page,
            "has_next_page": page.has_next_page,
        },
    }


def _comment_page_artifact(
    owner: str, repo: str, issue_number: int, issue_key: str, page: GitHubPage
) -> dict:
    return {
        "artifact_key": (f"github:{owner}/{repo}:issue:{issue_number}:comments:page:{page.page}"),
        "kind": "comment_page",
        "source_uri": (f"https://github.com/{owner}/{repo}/issues/{issue_number}?page={page.page}"),
        "raw": {
            "items": page.items,
            "page": page.page,
            "has_next_page": page.has_next_page,
        },
        "parent_artifact_key": issue_key,
    }


def _missing_field(payload: dict, fields: tuple[str, ...]) -> str | None:
    return next((field for field in fields if field not in payload), None)


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _result(
    *,
    raw_artifacts: list[dict],
    signals: list[SignalDraft],
    checkpoints: list[str],
    retry_count: int,
    issue_complete: bool,
    comments_complete: bool,
    parent_complete: bool,
    pagination_complete: bool,
    missing: list[str],
    terminal_state: str,
    failure_detail: str | None,
) -> GitHubMissionResult:
    return GitHubMissionResult(
        raw_artifacts=raw_artifacts,
        signals=signals,
        context_completeness=ContextCompleteness(
            issue_complete,
            comments_complete,
            parent_complete,
            pagination_complete,
            tuple(missing),
        ),
        checkpoints=checkpoints,
        retry_count=retry_count,
        terminal_state=terminal_state,
        failure_detail=failure_detail,
    )


class GitHubMissionAdapter:
    async def collect(
        self,
        source_url: str,
        config: SourceConfigVersion,
        transport: GitHubMissionTransport,
        *,
        item_limit: int,
    ) -> GitHubMissionResult:
        owner, repo = _repository_coordinates(source_url)
        retry_limit = config.request_policy.get("retry_limit", 0)
        issue_fetch = await _fetch_page(
            lambda: transport.list_issues(owner, repo, config.query_scope["query_terms"]),
            owner=owner,
            repo=repo,
            stage="issues",
            retry_limit=retry_limit,
        )
        raw_artifacts = list(issue_fetch.raw_artifacts)
        checkpoints = list(issue_fetch.checkpoints)
        retry_count = issue_fetch.retry_count
        if issue_fetch.page is None:
            error_messages: dict[str, str] = {
                "budget_exhausted": "Request budget exhausted while retrying GitHub issues.",
                "rate_limited": (f"GitHub rate limit persisted after {retry_limit} retry."),
            }
            detail = error_messages.get(
                issue_fetch.error_kind or "",
                issue_fetch.error_detail or "GitHub issue transport failed.",
            )
            return _result(
                raw_artifacts=raw_artifacts,
                signals=[],
                checkpoints=checkpoints,
                retry_count=retry_count,
                issue_complete=False,
                comments_complete=False,
                parent_complete=False,
                pagination_complete=False,
                missing=["issue_page", "comments", "parent_context"],
                terminal_state="failed",
                failure_detail=detail,
            )

        issue_page = issue_fetch.page
        raw_artifacts.append(_issue_page_artifact(owner, repo, issue_page))
        checkpoints.append(f"issues:page:{issue_page.page}")
        if not issue_page.items:
            return _result(
                raw_artifacts=raw_artifacts,
                signals=[],
                checkpoints=checkpoints,
                retry_count=retry_count,
                issue_complete=False,
                comments_complete=False,
                parent_complete=False,
                pagination_complete=not issue_page.has_next_page,
                missing=["matching_issues"],
                terminal_state="empty",
                failure_detail="No GitHub issues matched the pinned query.",
            )

        signals: list[SignalDraft] = []
        missing: list[str] = []
        parent_complete = True
        comments_complete = True
        pagination_complete = not issue_page.has_next_page
        if issue_page.has_next_page:
            _append_unique(missing, "additional_pages")

        for issue in issue_page.items:
            if len(signals) >= item_limit:
                _append_unique(missing, "item_limit")
                pagination_complete = False
                break
            missing_field = _missing_field(
                issue, ("number", "title", "body", "html_url", "created_at")
            )
            if missing_field is not None:
                checkpoints.append(f"issues:page:{issue_page.page}:parse_failed")
                return _result(
                    raw_artifacts=raw_artifacts,
                    signals=signals,
                    checkpoints=checkpoints,
                    retry_count=retry_count,
                    issue_complete=parent_complete and bool(signals),
                    comments_complete=False,
                    parent_complete=parent_complete,
                    pagination_complete=False,
                    missing=["parser_output"],
                    terminal_state="partial" if signals else "failed",
                    failure_detail=(
                        f"GitHub issue parser could not read required field: {missing_field}."
                    ),
                )
            try:
                issue_number = int(issue["number"])
                issue_title = issue["title"]
                issue_body = issue["body"]
                issue_url = issue["html_url"]
                observed_at = datetime.fromisoformat(issue["created_at"])
                if not isinstance(issue_title, str) or not isinstance(issue_url, str):
                    raise TypeError
                if issue_body is not None and not isinstance(issue_body, str):
                    raise TypeError
            except (TypeError, ValueError):
                checkpoints.append(f"issue:{issue.get('number', 'unknown')}:parse_failed")
                return _result(
                    raw_artifacts=raw_artifacts,
                    signals=signals,
                    checkpoints=checkpoints,
                    retry_count=retry_count,
                    issue_complete=parent_complete and bool(signals),
                    comments_complete=False,
                    parent_complete=parent_complete,
                    pagination_complete=False,
                    missing=["parser_output"],
                    terminal_state="partial" if signals else "failed",
                    failure_detail="GitHub issue parser rejected invalid field values.",
                )

            issue_key = f"github:{owner}/{repo}:issue:{issue_number}"
            raw_artifacts.append(
                {
                    "artifact_key": issue_key,
                    "kind": "issue",
                    "source_uri": issue_url,
                    "raw": issue,
                }
            )
            parent_available = bool(issue.get("parent_available", True))
            issue_context: dict = {
                "issue_number": issue_number,
                "pagination_complete": False,
            }
            if parent_available:
                issue_context["issue_title"] = issue_title
                signals.append(
                    SignalDraft(
                        lineage_key=issue_key,
                        raw_artifact_key=issue_key,
                        source_label=f"GitHub {owner}/{repo} issue #{issue_number}",
                        source_uri=issue_url,
                        original_material=(
                            f"{issue_title}\n\n{issue_body}" if issue_body else issue_title
                        ),
                        observed_at=observed_at,
                        observation=_evidence_observation("issue", issue_title, issue_body),
                        parent_context_available=True,
                        context_snapshot=issue_context,
                    )
                )
            else:
                parent_complete = False
                _append_unique(missing, "issue_parent")
                issue_context["missing"] = ["issue_parent"]

            comment_stage = f"issue:{issue_number}:comments"
            comment_fetch = await _fetch_page(
                partial(transport.list_issue_comments, owner, repo, issue_number),
                owner=owner,
                repo=repo,
                stage=comment_stage,
                retry_limit=retry_limit,
            )
            raw_artifacts.extend(comment_fetch.raw_artifacts)
            checkpoints.extend(comment_fetch.checkpoints)
            retry_count += comment_fetch.retry_count
            if comment_fetch.page is None:
                comments_complete = False
                pagination_complete = False
                _append_unique(missing, "comments")
                error_messages = {
                    "budget_exhausted": (
                        "Request budget exhausted before comment context was collected."
                    ),
                    "rate_limited": (
                        f"GitHub comment rate limit persisted after {retry_limit} retry."
                    ),
                }
                detail = error_messages.get(
                    comment_fetch.error_kind or "",
                    comment_fetch.error_detail or "GitHub comment transport failed.",
                )
                return _result(
                    raw_artifacts=raw_artifacts,
                    signals=signals,
                    checkpoints=checkpoints,
                    retry_count=retry_count,
                    issue_complete=parent_complete and bool(signals),
                    comments_complete=False,
                    parent_complete=parent_complete,
                    pagination_complete=False,
                    missing=missing,
                    terminal_state="partial",
                    failure_detail=detail,
                )

            comment_page = comment_fetch.page
            raw_artifacts.append(
                _comment_page_artifact(owner, repo, issue_number, issue_key, comment_page)
            )
            checkpoints.append(f"issue:{issue_number}:comments:page:{comment_page.page}")
            if comment_page.has_next_page:
                pagination_complete = False
                _append_unique(missing, "additional_pages")
            issue_context["pagination_complete"] = (
                not issue_page.has_next_page and not comment_page.has_next_page
            )

            for comment in comment_page.items:
                if len(signals) >= item_limit:
                    pagination_complete = False
                    _append_unique(missing, "item_limit")
                    break
                missing_field = _missing_field(comment, ("id", "body", "html_url", "created_at"))
                if missing_field is not None:
                    checkpoints.append(
                        f"issue:{issue_number}:comments:page:{comment_page.page}:parse_failed"
                    )
                    return _result(
                        raw_artifacts=raw_artifacts,
                        signals=signals,
                        checkpoints=checkpoints,
                        retry_count=retry_count,
                        issue_complete=parent_complete and bool(signals),
                        comments_complete=False,
                        parent_complete=parent_complete,
                        pagination_complete=False,
                        missing=["comment_parser_output"],
                        terminal_state="partial",
                        failure_detail=(
                            f"GitHub comment parser could not read required field: {missing_field}."
                        ),
                    )
                try:
                    comment_id = int(comment["id"])
                    comment_body = comment["body"]
                    comment_url = comment["html_url"]
                    comment_time = datetime.fromisoformat(comment["created_at"])
                    if not isinstance(comment_body, str) or not isinstance(comment_url, str):
                        raise TypeError
                except (TypeError, ValueError):
                    checkpoints.append(
                        f"issue:{issue_number}:comments:page:{comment_page.page}:parse_failed"
                    )
                    return _result(
                        raw_artifacts=raw_artifacts,
                        signals=signals,
                        checkpoints=checkpoints,
                        retry_count=retry_count,
                        issue_complete=parent_complete and bool(signals),
                        comments_complete=False,
                        parent_complete=parent_complete,
                        pagination_complete=False,
                        missing=["comment_parser_output"],
                        terminal_state="partial",
                        failure_detail=("GitHub comment parser rejected invalid field values."),
                    )
                comment_key = f"github:{owner}/{repo}:comment:{comment_id}"
                raw_artifacts.append(
                    {
                        "artifact_key": comment_key,
                        "kind": "comment",
                        "source_uri": comment_url,
                        "raw": comment,
                        "parent_artifact_key": issue_key,
                    }
                )
                signals.append(
                    SignalDraft(
                        lineage_key=comment_key,
                        raw_artifact_key=comment_key,
                        source_label=(f"GitHub {owner}/{repo} issue #{issue_number} comment"),
                        source_uri=comment_url,
                        original_material=comment_body,
                        observed_at=comment_time,
                        observation=_evidence_observation("comment", comment_body),
                        parent_context_available=parent_available,
                        context_snapshot=issue_context,
                    )
                )

        if missing:
            details = []
            if "issue_parent" in missing:
                details.append("Parent issue context was unavailable.")
            if "additional_pages" in missing:
                details.append("Additional GitHub pages remain outside this bounded run.")
            if "item_limit" in missing:
                details.append("Mission item limit left collected items unprocessed.")
            return _result(
                raw_artifacts=raw_artifacts,
                signals=signals,
                checkpoints=checkpoints,
                retry_count=retry_count,
                issue_complete=parent_complete and bool(signals),
                comments_complete=comments_complete,
                parent_complete=parent_complete,
                pagination_complete=pagination_complete,
                missing=missing,
                terminal_state="partial",
                failure_detail=" ".join(details),
            )
        return _result(
            raw_artifacts=raw_artifacts,
            signals=signals,
            checkpoints=checkpoints,
            retry_count=retry_count,
            issue_complete=True,
            comments_complete=True,
            parent_complete=True,
            pagination_complete=True,
            missing=[],
            terminal_state="succeeded",
            failure_detail=None,
        )
