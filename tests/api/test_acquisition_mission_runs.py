"""Behavior tests for running pinned missions into the Evidence Inbox."""

from apps.api.dependencies import (
    get_github_live_transport,
    get_github_mission_transport,
)
from apps.api.main import app
from packages.adapters.github_mission import GitHubFixtureTransport, GitHubPage


async def _create_github_mission(client, *, request_limit=3, retry_limit=1, timeout_seconds=10):
    source_response = await client.post(
        "/api/sources",
        json={
            "name": "GitHub payment reconciliation issues",
            "platform": "github",
            "source_type": "issues",
            "url": "https://github.com/example/payments/issues",
        },
    )
    assert source_response.status_code == 201
    source = source_response.json()

    config_response = await client.post(
        f"/api/sources/{source['id']}/config-versions",
        json={
            "access_mode": "public",
            "query_scope": {"query_terms": ["reconciliation", "payout"]},
            "request_policy": {
                "request_limit": request_limit,
                "timeout_seconds": timeout_seconds,
                "retry_limit": retry_limit,
            },
            "pagination_context_rules": {
                "page_limit": 2,
                "include_replies": True,
                "require_parent_context": True,
            },
            "extraction_settings": {
                "parser": "github_issue",
                "parser_version": "v1",
                "content_fields": ["title", "body", "comments"],
            },
        },
    )
    assert config_response.status_code == 201
    config = config_response.json()

    mission_response = await client.post(
        "/api/acquisition-missions",
        json={
            "reality_question": "Where does payout reconciliation create observable work?",
            "mission_type": "targeted_evidence",
            "source_id": source["id"],
            "source_config_version_id": config["id"],
            "regions": ["global"],
            "languages": ["en"],
            "target_audience": "independent developers receiving payouts",
            "query_seeds": ["reconciliation", "payout"],
            "time_budget_minutes": 10,
            "item_limit": 20,
            "cost_budget_cents": 0,
            "stop_conditions": ["Capture one issue with its comment context"],
        },
    )
    assert mission_response.status_code == 201
    return mission_response.json(), config


async def test_fixture_github_mission_preserves_raw_context_and_creates_traceable_signals(client):
    mission, config = await _create_github_mission(client)
    app.dependency_overrides[get_github_mission_transport] = lambda: GitHubFixtureTransport(
        scenario="issue_with_context"
    )

    created = await client.post(
        f"/api/acquisition-missions/{mission['id']}/runs",
        json={"execution_mode": "fixture"},
    )

    assert created.status_code == 201
    run = created.json()
    assert run["mission_id"] == mission["id"]
    assert run["source_config_version_id"] == config["id"]
    assert run["terminal_state"] == "succeeded"
    assert run["execution_mode"] == "fixture"
    assert run["budgets"] == {
        "request_limit": 3,
        "time_limit_seconds": 10,
        "item_limit": 20,
        "cost_budget_cents": 0,
    }
    assert run["parser_version"] == "github_issue:v1"
    assert run["input_snapshot"]["mission"]["reality_question"] == (
        "Where does payout reconciliation create observable work?"
    )
    assert run["input_snapshot"]["source_config_version"]["id"] == config["id"]
    assert run["input_snapshot"]["source_config_version"]["query_scope"] == {
        "query_terms": ["reconciliation", "payout"],
        "filters": {},
        "exclusions": [],
    }
    assert run["context_completeness"] == {
        "issue": True,
        "comments": True,
        "parent_context": True,
        "pagination_complete": True,
        "missing": [],
    }
    assert run["checkpoints"] == ["issues:page:1", "issue:42:comments:page:1"]
    assert run["retry_count"] == 0
    assert run["transport_requests"] == 2
    assert run["network_requests"] == 0
    assert len(run["raw_artifacts"]) == 2
    assert run["raw_artifacts"][0]["artifact_key"] == "github:example/payments:issue:42"
    assert run["raw_artifacts"][1]["artifact_key"] == "github:example/payments:comment:4201"
    assert len(run["external_signal_ids"]) == 2

    retrieved = await client.get(f"/api/acquisition-mission-runs/{run['id']}")
    inbox = await client.get("/api/evidence-inbox")

    assert retrieved.status_code == 200
    assert retrieved.json() == run
    assert inbox.status_code == 200
    signals = inbox.json()["items"]
    assert {signal["id"] for signal in signals} == set(run["external_signal_ids"])
    assert {signal["lineage_key"] for signal in signals} == {
        "github:example/payments:issue:42",
        "github:example/payments:comment:4201",
    }
    comment_signal = next(signal for signal in signals if ":comment:" in signal["lineage_key"])
    assert comment_signal["mission_run_id"] == run["id"]
    assert comment_signal["parent_context_available"] is True
    assert comment_signal["context_snapshot"]["issue_number"] == 42
    assert comment_signal["context_snapshot"]["pagination_complete"] is True


async def test_live_mode_uses_the_public_transport_and_records_network_requests(client):
    class NetworkFixtureTransport(GitHubFixtureTransport):
        async def list_issues(self, owner, repo, query_terms):
            self.network_requests += 1
            return await super().list_issues(owner, repo, query_terms)

        async def list_issue_comments(self, owner, repo, issue_number):
            self.network_requests += 1
            return await super().list_issue_comments(owner, repo, issue_number)

    mission, _ = await _create_github_mission(client)
    app.dependency_overrides[get_github_live_transport] = lambda: NetworkFixtureTransport(
        scenario="issue_with_context"
    )

    created = await client.post(
        f"/api/acquisition-missions/{mission['id']}/runs",
        json={"execution_mode": "live"},
    )

    assert created.status_code == 201
    run = created.json()
    assert run["execution_mode"] == "live"
    assert run["terminal_state"] == "succeeded"
    assert run["transport_requests"] == 2
    assert run["network_requests"] == 2


async def test_live_issue_without_comments_remains_real_evidence_without_invented_claims(client):
    class NoCommentsTransport:
        transport_requests = 0
        network_requests = 0

        async def list_issues(self, owner, repo, query_terms):
            self.transport_requests += 1
            self.network_requests += 1
            return GitHubPage(
                items=[
                    {
                        "number": 7,
                        "title": "Plugin setup requires repeated manual mapping",
                        "body": "Each workspace needs the same fields mapped again.",
                        "html_url": f"https://github.com/{owner}/{repo}/issues/7",
                        "created_at": "2026-07-31T08:00:00+00:00",
                    }
                ],
                page=1,
                has_next_page=False,
            )

        async def list_issue_comments(self, owner, repo, issue_number):
            self.transport_requests += 1
            self.network_requests += 1
            return GitHubPage(items=[], page=1, has_next_page=False)

    mission, _ = await _create_github_mission(client)
    app.dependency_overrides[get_github_live_transport] = lambda: NoCommentsTransport()

    created = await client.post(
        f"/api/acquisition-missions/{mission['id']}/runs",
        json={"execution_mode": "live"},
    )

    assert created.status_code == 201
    run = created.json()
    assert run["terminal_state"] == "succeeded"
    assert run["context_completeness"] == {
        "issue": True,
        "comments": True,
        "parent_context": True,
        "pagination_complete": True,
        "missing": [],
    }
    assert [artifact["kind"] for artifact in run["raw_artifacts"]] == [
        "issue",
        "comment_page",
    ]
    assert len(run["external_signal_ids"]) == 1

    inbox = await client.get("/api/evidence-inbox")
    signal = inbox.json()["items"][0]
    assert "Plugin setup requires repeated manual mapping" in signal["observation"]
    assert "three hours" not in signal["observation"]


async def test_missing_parent_context_is_a_partial_run_and_visible_on_the_signal(client):
    mission, _ = await _create_github_mission(client)
    app.dependency_overrides[get_github_mission_transport] = lambda: GitHubFixtureTransport(
        scenario="missing_parent"
    )

    created = await client.post(
        f"/api/acquisition-missions/{mission['id']}/runs",
        json={"execution_mode": "fixture"},
    )

    assert created.status_code == 201
    run = created.json()
    assert run["terminal_state"] == "partial"
    assert run["failure_detail"] == "Parent issue context was unavailable."
    assert run["context_completeness"] == {
        "issue": False,
        "comments": True,
        "parent_context": False,
        "pagination_complete": True,
        "missing": ["issue_parent"],
    }
    assert len(run["external_signal_ids"]) == 1

    inbox = await client.get("/api/evidence-inbox")
    signal = inbox.json()["items"][0]
    assert signal["id"] == run["external_signal_ids"][0]
    assert signal["parent_context_available"] is False
    assert signal["context_snapshot"]["missing"] == ["issue_parent"]


async def test_empty_github_result_is_visible_and_creates_no_signal(client):
    mission, _ = await _create_github_mission(client)
    app.dependency_overrides[get_github_mission_transport] = lambda: GitHubFixtureTransport(
        scenario="empty"
    )

    created = await client.post(
        f"/api/acquisition-missions/{mission['id']}/runs",
        json={"execution_mode": "fixture"},
    )

    assert created.status_code == 201
    run = created.json()
    assert run["terminal_state"] == "empty"
    assert run["failure_detail"] == "No GitHub issues matched the pinned query."
    assert run["transport_requests"] == 1
    assert run["checkpoints"] == ["issues:page:1"]
    assert run["external_signal_ids"] == []
    assert run["raw_artifacts"] == [
        {
            "artifact_key": "github:example/payments:issues:page:1",
            "kind": "issue_page",
            "source_uri": "https://github.com/example/payments/issues?page=1",
            "raw": {"items": [], "has_next_page": False},
        }
    ]

    inbox = await client.get("/api/evidence-inbox")
    assert inbox.json()["items"] == []


async def test_rate_limit_exhausts_configured_retry_and_remains_a_failed_run(client):
    mission, _ = await _create_github_mission(client)
    app.dependency_overrides[get_github_mission_transport] = lambda: GitHubFixtureTransport(
        scenario="rate_limited"
    )

    created = await client.post(
        f"/api/acquisition-missions/{mission['id']}/runs",
        json={"execution_mode": "fixture"},
    )

    assert created.status_code == 201
    run = created.json()
    assert run["terminal_state"] == "failed"
    assert run["failure_detail"] == "GitHub rate limit persisted after 1 retry."
    assert run["retry_count"] == 1
    assert run["transport_requests"] == 2
    assert run["checkpoints"] == [
        "issues:attempt:1:rate_limited",
        "issues:attempt:2:rate_limited",
    ]
    assert [artifact["raw"]["status"] for artifact in run["raw_artifacts"]] == [429, 429]
    assert run["external_signal_ids"] == []

    inbox = await client.get("/api/evidence-inbox")
    assert inbox.json()["items"] == []


async def test_parsing_failure_preserves_raw_page_and_creates_no_signal(client):
    mission, _ = await _create_github_mission(client)
    app.dependency_overrides[get_github_mission_transport] = lambda: GitHubFixtureTransport(
        scenario="parsing_failure"
    )

    created = await client.post(
        f"/api/acquisition-missions/{mission['id']}/runs",
        json={"execution_mode": "fixture"},
    )

    assert created.status_code == 201
    run = created.json()
    assert run["terminal_state"] == "failed"
    assert run["failure_detail"] == "GitHub issue parser could not read required field: number."
    assert run["parser_version"] == "github_issue:v1"
    assert run["transport_requests"] == 1
    assert run["checkpoints"] == ["issues:page:1", "issues:page:1:parse_failed"]
    assert run["raw_artifacts"][0]["raw"]["items"] == [
        {"title": "Malformed fixture without an issue number"}
    ]
    assert run["external_signal_ids"] == []


async def test_fixture_replay_reuses_lineage_without_transport_or_duplicate_signals(client):
    mission, _ = await _create_github_mission(client)
    app.dependency_overrides[get_github_mission_transport] = lambda: GitHubFixtureTransport(
        scenario="issue_with_context"
    )
    original_response = await client.post(
        f"/api/acquisition-missions/{mission['id']}/runs",
        json={"execution_mode": "fixture"},
    )
    original = original_response.json()

    replay_response = await client.post(f"/api/acquisition-mission-runs/{original['id']}/replay")

    assert replay_response.status_code == 201
    replay = replay_response.json()
    assert replay["id"] != original["id"]
    assert replay["replay_of_run_id"] == original["id"]
    assert replay["execution_mode"] == "fixture_replay"
    assert replay["raw_artifacts"] == original["raw_artifacts"]
    assert replay["input_snapshot"] == original["input_snapshot"]
    assert replay["parser_version"] == original["parser_version"]
    assert replay["external_signal_ids"] == original["external_signal_ids"]
    assert replay["transport_requests"] == 0
    assert replay["network_requests"] == 0

    inbox = await client.get("/api/evidence-inbox")
    assert len(inbox.json()["items"]) == 2
    assert {item["id"] for item in inbox.json()["items"]} == set(original["external_signal_ids"])


async def test_repeated_mission_run_reuses_existing_business_lineage(client):
    mission, _ = await _create_github_mission(client)
    app.dependency_overrides[get_github_mission_transport] = lambda: GitHubFixtureTransport(
        scenario="issue_with_context"
    )

    first_response = await client.post(
        f"/api/acquisition-missions/{mission['id']}/runs",
        json={"execution_mode": "fixture"},
    )
    second_response = await client.post(
        f"/api/acquisition-missions/{mission['id']}/runs",
        json={"execution_mode": "fixture"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert (
        second_response.json()["external_signal_ids"]
        == first_response.json()["external_signal_ids"]
    )
    inbox = await client.get("/api/evidence-inbox")
    assert len(inbox.json()["items"]) == 2


async def test_request_budget_stops_before_comment_fetch_and_preserves_partial_issue(client):
    mission, _ = await _create_github_mission(client, request_limit=1)
    app.dependency_overrides[get_github_mission_transport] = lambda: GitHubFixtureTransport(
        scenario="issue_with_context"
    )

    created = await client.post(
        f"/api/acquisition-missions/{mission['id']}/runs",
        json={"execution_mode": "fixture"},
    )

    assert created.status_code == 201
    run = created.json()
    assert run["terminal_state"] == "partial"
    assert run["failure_detail"] == (
        "Request budget exhausted before comment context was collected."
    )
    assert run["transport_requests"] == 1
    assert run["context_completeness"] == {
        "issue": True,
        "comments": False,
        "parent_context": True,
        "pagination_complete": False,
        "missing": ["comments"],
    }
    assert run["checkpoints"] == [
        "issues:page:1",
        "issue:42:comments:budget_exhausted",
    ]
    assert [artifact["kind"] for artifact in run["raw_artifacts"]] == ["issue"]
    assert len(run["external_signal_ids"]) == 1


async def test_time_budget_cancels_hanging_transport_and_persists_failed_run(client):
    class HangingTransport:
        transport_requests = 0
        network_requests = 0

        async def list_issues(self, owner, repo, query_terms):
            import asyncio

            self.transport_requests += 1
            self.network_requests += 1
            await asyncio.sleep(2)

        async def list_issue_comments(self, owner, repo, issue_number):
            raise AssertionError("comments must not be requested after timeout")

    mission, _ = await _create_github_mission(client, timeout_seconds=1)
    app.dependency_overrides[get_github_mission_transport] = lambda: HangingTransport()

    created = await client.post(
        f"/api/acquisition-missions/{mission['id']}/runs",
        json={"execution_mode": "fixture"},
    )

    assert created.status_code == 201
    run = created.json()
    assert run["terminal_state"] == "failed"
    assert run["failure_detail"] == "Mission exceeded its 1 second time budget."
    assert run["transport_requests"] == 1
    assert run["network_requests"] == 1
    assert run["checkpoints"] == ["run:timeout"]
    assert run["external_signal_ids"] == []
