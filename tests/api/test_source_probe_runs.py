"""Behavior tests for bounded probes of immutable source configurations."""

import asyncio

import pytest

from apps.api.dependencies import get_source_probe_adapter
from apps.api.main import app
from packages.adapters.source_probe import ProbeRequest, ProbeResult
from tests.factories import create_source


async def _create_config(client, db, scenario="accessible_with_context"):
    source = await create_source(
        db,
        name=f"Fixture source: {scenario}",
        platform="fixture",
        source_type=scenario,
        url=f"fixture://{scenario}",
    )
    response = await client.post(
        f"/api/sources/{source.id}/config-versions",
        json={
            "access_mode": "public",
            "query_scope": {"query_terms": ["feedback"]},
            "request_policy": {"request_limit": 2, "timeout_seconds": 10},
            "pagination_context_rules": {
                "page_limit": 1,
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
    assert response.status_code == 201
    return source, response.json()


async def test_operator_can_run_and_retrieve_a_bounded_probe(client, db):
    source, config = await _create_config(client, db)

    created = await client.post(
        f"/api/sources/{source.id}/config-versions/{config['version']}/probes",
        json={"request_budget": 2, "time_budget_seconds": 5},
    )

    assert created.status_code == 201
    body = created.json()
    assert body["source_config_version_id"] == config["id"]
    assert body["status"] == "succeeded"
    assert body["access_state"] == "public"
    assert body["sample_available"] is True
    assert body["sample"] == {
        "title": "Users need reply context",
        "body": "The top-level comment is ambiguous without its parent discussion.",
    }
    assert body["pagination_supported"] is True
    assert body["replies_supported"] is True
    assert body["context_risks"] == []
    assert body["consumed_requests"] == 1
    assert body["consumed_requests"] <= body["request_budget"]
    assert body["elapsed_ms"] <= body["time_budget_seconds"] * 1000

    retrieved = await client.get(f"/api/source-probes/{body['id']}")

    assert retrieved.status_code == 200
    assert retrieved.json() == body


async def test_empty_probe_is_visible_and_never_reported_as_success(client, db):
    source, config = await _create_config(client, db, scenario="empty_result")

    response = await client.post(
        f"/api/sources/{source.id}/config-versions/{config['version']}/probes",
        json={"request_budget": 2, "time_budget_seconds": 5},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "empty"
    assert body["access_state"] == "public"
    assert body["sample_available"] is False
    assert body["sample"] is None
    assert body["outcome_detail"] == "No matching material was returned."
    assert body["consumed_requests"] == 1


async def test_rate_limit_is_reported_with_unverified_context_capabilities(client, db):
    source, config = await _create_config(client, db, scenario="rate_limited")

    response = await client.post(
        f"/api/sources/{source.id}/config-versions/{config['version']}/probes",
        json={"request_budget": 2, "time_budget_seconds": 5},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["access_state"] == "rate_limited"
    assert body["sample_available"] is False
    assert body["pagination_supported"] is None
    assert body["replies_supported"] is None
    assert body["context_risks"] == [
        "Pagination and reply context could not be verified because the source "
        "rate-limited the probe."
    ]
    assert body["outcome_detail"] == "rate_limited"


async def test_runtime_stops_a_probe_at_its_time_budget_and_records_failure(client, db):
    class HangingAdapter:
        async def probe(self, source, config, *, execution):
            try:
                await asyncio.sleep(execution.time_limit_seconds + 1)
            except asyncio.CancelledError:
                await asyncio.sleep(0.05)
                return ProbeResult(
                    status="succeeded",
                    access_state="public",
                    sample={"title": "late", "body": "late"},
                    pagination_supported=True,
                    replies_supported=True,
                    context_risks=[],
                )

    source, config = await _create_config(client, db)
    app.dependency_overrides[get_source_probe_adapter] = lambda: HangingAdapter()

    response = await client.post(
        f"/api/sources/{source.id}/config-versions/{config['version']}/probes",
        json={"request_budget": 1, "time_budget_seconds": 1},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["access_state"] == "public"
    assert body["sample_available"] is False
    assert body["context_risks"] == ["Probe timed out before source capabilities were verified."]
    assert body["pagination_supported"] is None
    assert body["replies_supported"] is None
    assert body["elapsed_ms"] > body["time_budget_seconds"] * 1000
    assert body["outcome_detail"] == "probe_timeout"


async def test_runtime_refuses_requests_beyond_the_probe_budget(client, db):
    class GreedyAdapter:
        async def probe(self, source, config, *, execution):
            request = ProbeRequest(target="fixture://noop")
            await execution.request(request)
            await execution.request(request)

    source, config = await _create_config(client, db)
    app.dependency_overrides[get_source_probe_adapter] = lambda: GreedyAdapter()

    response = await client.post(
        f"/api/sources/{source.id}/config-versions/{config['version']}/probes",
        json={"request_budget": 1, "time_budget_seconds": 5},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["sample_available"] is False
    assert body["pagination_supported"] is None
    assert body["replies_supported"] is None
    assert body["consumed_requests"] == 1
    assert body["consumed_requests"] <= body["request_budget"]
    assert body["context_risks"] == ["Probe exhausted its request budget before completion."]
    assert body["outcome_detail"] == "request_budget_exhausted"


async def test_adapter_error_is_persisted_as_a_structured_failed_probe(client, db):
    class BrokenAdapter:
        async def probe(self, source, config, *, execution):
            raise OSError("DNS lookup failed")

    source, config = await _create_config(client, db)
    app.dependency_overrides[get_source_probe_adapter] = lambda: BrokenAdapter()

    response = await client.post(
        f"/api/sources/{source.id}/config-versions/{config['version']}/probes",
        json={"request_budget": 1, "time_budget_seconds": 5},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["sample_available"] is False
    assert body["context_risks"] == ["Probe adapter failed before capabilities were verified."]
    assert body["outcome_detail"] == "adapter_error:OSError"


@pytest.mark.parametrize(
    ("scenario", "expected_state"),
    [
        ("credentialed", "credentialed"),
        ("subscription_gated", "subscription"),
        ("blocked", "blocked"),
    ],
)
async def test_fixture_reports_non_public_access_states(client, db, scenario, expected_state):
    source, config = await _create_config(client, db, scenario=scenario)

    response = await client.post(
        f"/api/sources/{source.id}/config-versions/{config['version']}/probes",
        json={"request_budget": 1, "time_budget_seconds": 5},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["access_state"] == expected_state
    assert body["sample_available"] is False
    assert body["pagination_supported"] is None
    assert body["replies_supported"] is None
    assert body["context_risks"]
