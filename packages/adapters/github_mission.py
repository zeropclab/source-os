"""Parse bounded GitHub pages into raw artifacts and traceable evidence signals."""

from dataclasses import dataclass
from datetime import datetime
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
from packages.storage.models.acquisition_mission import AcquisitionMission
from packages.storage.models.source import Source
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


def _repository_coordinates(source: Source) -> tuple[str, str]:
    parsed = urlparse(source.url)
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


def _terminal_outcome(
    *, parent_available: bool, pagination_complete: bool
) -> tuple[str, str | None, tuple[str, ...]]:
    missing = []
    details = []
    if not parent_available:
        missing.append("issue_parent")
        details.append("Parent issue context was unavailable.")
    if not pagination_complete:
        missing.append("additional_pages")
        details.append("Additional GitHub pages remain outside this bounded run.")
    if missing:
        return "partial", " ".join(details), tuple(missing)
    return "succeeded", None, ()


class GitHubMissionAdapter:
    async def collect(
        self,
        source: Source,
        config: SourceConfigVersion,
        mission: AcquisitionMission,
        transport: GitHubMissionTransport,
    ) -> GitHubMissionResult:
        del mission
        owner, repo = _repository_coordinates(source)
        retry_limit = config.request_policy.get("retry_limit", 0)
        raw_artifacts: list[dict] = []
        checkpoints: list[str] = []

        issue_page: GitHubPage | None = None
        issue_retries = 0
        for attempt in range(1, retry_limit + 2):
            try:
                issue_page = await transport.list_issues(
                    owner, repo, config.query_scope["query_terms"]
                )
                issue_retries = attempt - 1
                break
            except GitHubRateLimitError:
                checkpoints.append(f"issues:attempt:{attempt}:rate_limited")
                raw_artifacts.append(
                    _transport_failure_artifact(
                        owner=owner,
                        repo=repo,
                        stage="issues",
                        attempt=attempt,
                        status=429,
                        detail="rate_limited",
                    )
                )
            except GitHubRequestBudgetExceededError:
                checkpoints.append(f"issues:attempt:{attempt}:budget_exhausted")
                return GitHubMissionResult(
                    raw_artifacts=raw_artifacts,
                    signals=[],
                    context_completeness=ContextCompleteness(
                        False,
                        False,
                        False,
                        False,
                        ("issue_page", "comments", "parent_context"),
                    ),
                    checkpoints=checkpoints,
                    retry_count=max(0, attempt - 1),
                    terminal_state="failed",
                    failure_detail="Request budget exhausted while retrying GitHub issues.",
                )
            except GitHubTransportError as exc:
                checkpoints.append(f"issues:attempt:{attempt}:transport_failed")
                raw_artifacts.append(
                    _transport_failure_artifact(
                        owner=owner,
                        repo=repo,
                        stage="issues",
                        attempt=attempt,
                        status=exc.status_code,
                        detail=exc.detail,
                    )
                )
                return GitHubMissionResult(
                    raw_artifacts=raw_artifacts,
                    signals=[],
                    context_completeness=ContextCompleteness(
                        False,
                        False,
                        False,
                        False,
                        ("issue_page", "comments", "parent_context"),
                    ),
                    checkpoints=checkpoints,
                    retry_count=max(0, attempt - 1),
                    terminal_state="failed",
                    failure_detail=exc.detail,
                )

        if issue_page is None:
            return GitHubMissionResult(
                raw_artifacts=raw_artifacts,
                signals=[],
                context_completeness=ContextCompleteness(
                    False,
                    False,
                    False,
                    False,
                    ("issue_page", "comments", "parent_context"),
                ),
                checkpoints=checkpoints,
                retry_count=retry_limit,
                terminal_state="failed",
                failure_detail=f"GitHub rate limit persisted after {retry_limit} retry.",
            )

        raw_artifacts.append(_issue_page_artifact(owner, repo, issue_page))
        checkpoints.append(f"issues:page:{issue_page.page}")
        if not issue_page.items:
            return GitHubMissionResult(
                raw_artifacts=raw_artifacts,
                signals=[],
                context_completeness=ContextCompleteness(
                    False,
                    False,
                    False,
                    not issue_page.has_next_page,
                    ("matching_issues",),
                ),
                checkpoints=checkpoints,
                retry_count=issue_retries,
                terminal_state="empty",
                failure_detail="No GitHub issues matched the pinned query.",
            )

        issue = issue_page.items[0]
        required_issue_fields = ["number", "title", "body", "html_url", "created_at"]
        missing_issue_field = next(
            (field for field in required_issue_fields if field not in issue), None
        )
        if missing_issue_field is not None:
            checkpoints.append(f"issues:page:{issue_page.page}:parse_failed")
            return GitHubMissionResult(
                raw_artifacts=raw_artifacts,
                signals=[],
                context_completeness=ContextCompleteness(
                    False, False, False, not issue_page.has_next_page, ("parser_output",)
                ),
                checkpoints=checkpoints,
                retry_count=issue_retries,
                terminal_state="failed",
                failure_detail=(
                    f"GitHub issue parser could not read required field: {missing_issue_field}."
                ),
            )

        issue_key = f"github:{owner}/{repo}:issue:{issue['number']}"
        issue_artifact = {
            "artifact_key": issue_key,
            "kind": "issue",
            "source_uri": issue["html_url"],
            "raw": issue,
        }
        raw_artifacts.append(issue_artifact)
        parent_available = issue.get("parent_available", True)
        issue_context = {
            "issue_number": issue["number"],
            "pagination_complete": False,
        }
        issue_signal = None
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

        comment_page: GitHubPage | None = None
        comment_retries = 0
        for attempt in range(1, retry_limit + 2):
            try:
                comment_page = await transport.list_issue_comments(owner, repo, issue["number"])
                comment_retries = attempt - 1
                break
            except GitHubRateLimitError:
                checkpoints.append(
                    f"issue:{issue['number']}:comments:attempt:{attempt}:rate_limited"
                )
                raw_artifacts.append(
                    _transport_failure_artifact(
                        owner=owner,
                        repo=repo,
                        stage=f"issue:{issue['number']}:comments",
                        attempt=attempt,
                        status=429,
                        detail="rate_limited",
                    )
                )
            except GitHubRequestBudgetExceededError:
                checkpoints.append(f"issue:{issue['number']}:comments:budget_exhausted")
                return GitHubMissionResult(
                    raw_artifacts=raw_artifacts,
                    signals=[] if issue_signal is None else [issue_signal],
                    context_completeness=ContextCompleteness(
                        parent_available,
                        False,
                        parent_available,
                        False,
                        ("comments",),
                    ),
                    checkpoints=checkpoints,
                    retry_count=issue_retries + max(0, attempt - 1),
                    terminal_state="partial",
                    failure_detail=(
                        "Request budget exhausted before comment context was collected."
                    ),
                )
            except GitHubTransportError as exc:
                checkpoints.append(
                    f"issue:{issue['number']}:comments:attempt:{attempt}:transport_failed"
                )
                raw_artifacts.append(
                    _transport_failure_artifact(
                        owner=owner,
                        repo=repo,
                        stage=f"issue:{issue['number']}:comments",
                        attempt=attempt,
                        status=exc.status_code,
                        detail=exc.detail,
                    )
                )
                return GitHubMissionResult(
                    raw_artifacts=raw_artifacts,
                    signals=[] if issue_signal is None else [issue_signal],
                    context_completeness=ContextCompleteness(
                        parent_available,
                        False,
                        parent_available,
                        False,
                        ("comments",),
                    ),
                    checkpoints=checkpoints,
                    retry_count=issue_retries + max(0, attempt - 1),
                    terminal_state="partial",
                    failure_detail=exc.detail,
                )

        if comment_page is None:
            return GitHubMissionResult(
                raw_artifacts=raw_artifacts,
                signals=[] if issue_signal is None else [issue_signal],
                context_completeness=ContextCompleteness(
                    parent_available,
                    False,
                    parent_available,
                    False,
                    ("comments",),
                ),
                checkpoints=checkpoints,
                retry_count=issue_retries + retry_limit,
                terminal_state="partial",
                failure_detail=(f"GitHub comment rate limit persisted after {retry_limit} retry."),
            )

        raw_artifacts.append(
            _comment_page_artifact(owner, repo, issue["number"], issue_key, comment_page)
        )
        checkpoints.append(f"issue:{issue['number']}:comments:page:{comment_page.page}")
        pagination_complete = not issue_page.has_next_page and not comment_page.has_next_page
        issue_context["pagination_complete"] = pagination_complete
        terminal_state, failure_detail, missing = _terminal_outcome(
            parent_available=parent_available,
            pagination_complete=pagination_complete,
        )
        signals = [] if issue_signal is None else [issue_signal]

        if comment_page.items:
            comment = comment_page.items[0]
            required_comment_fields = ["id", "body", "html_url", "created_at"]
            missing_comment_field = next(
                (field for field in required_comment_fields if field not in comment), None
            )
            if missing_comment_field is not None:
                checkpoints.append(
                    f"issue:{issue['number']}:comments:page:{comment_page.page}:parse_failed"
                )
                return GitHubMissionResult(
                    raw_artifacts=raw_artifacts,
                    signals=signals,
                    context_completeness=ContextCompleteness(
                        parent_available,
                        False,
                        parent_available,
                        pagination_complete,
                        ("comment_parser_output",),
                    ),
                    checkpoints=checkpoints,
                    retry_count=issue_retries + comment_retries,
                    terminal_state="partial",
                    failure_detail=(
                        "GitHub comment parser could not read required field: "
                        f"{missing_comment_field}."
                    ),
                )
            comment_key = f"github:{owner}/{repo}:comment:{comment['id']}"
            raw_artifacts.append(
                {
                    "artifact_key": comment_key,
                    "kind": "comment",
                    "source_uri": comment["html_url"],
                    "raw": comment,
                    "parent_artifact_key": issue_key,
                }
            )
            signals.append(
                SignalDraft(
                    lineage_key=comment_key,
                    raw_artifact_key=comment_key,
                    source_label=(f"GitHub {owner}/{repo} issue #{issue['number']} comment"),
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
            context_completeness=ContextCompleteness(
                parent_available,
                True,
                parent_available,
                pagination_complete,
                missing,
            ),
            checkpoints=checkpoints,
            retry_count=issue_retries + comment_retries,
            terminal_state=terminal_state,
            failure_detail=failure_detail,
        )
