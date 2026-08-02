"""Configuration proposals remain evidence-bound and operator-controlled."""

from tests.factories import create_source


async def _config(client, source_id: str) -> dict:
    response = await client.post(
        f"/api/sources/{source_id}/config-versions",
        json={
            "access_mode": "public",
            "query_scope": {"query_terms": ["manual reconciliation"]},
            "request_policy": {"request_limit": 2, "timeout_seconds": 10},
            "pagination_context_rules": {"page_limit": 1},
            "extraction_settings": {
                "parser": "fixture",
                "parser_version": "v1",
                "content_fields": ["body"],
            },
        },
    )
    assert response.status_code == 201
    return response.json()


async def test_insufficient_source_artifacts_become_auditable_unknown_not_an_invented_fix(
    client, db
):
    source = await create_source(db)
    config = await _config(client, str(source.id))
    proposal = await client.post(
        "/api/source-config-proposals",
        json={
            "source_config_version_id": config["id"],
            "model_version": "pi-faux-v1",
            "prompt_version": "source-config-proposal-v1",
            "max_tokens": 200,
            "max_cost_cents": 2,
        },
    )

    assert proposal.status_code == 201
    data = proposal.json()
    assert data["status"] == "unknown"
    assert data["proposed_changes"] == {}
    assert data["evidence_refs"] == []

    rejected = await client.post(
        f"/api/source-config-proposals/{data['id']}/decisions",
        json={"decision": "rejected", "reason": "No evidence supports a configuration change."},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"


async def test_probe_evidence_is_cited_but_non_config_agent_output_cannot_apply_a_change(
    client, db
):
    source = await create_source(
        db,
        platform="fixture",
        source_type="accessible_with_context",
        url="fixture://accessible_with_context",
    )
    config = await _config(client, str(source.id))
    probe = await client.post(
        f"/api/sources/{source.id}/config-versions/{config['version']}/probes",
        json={"request_budget": 1, "time_budget_seconds": 5},
    )
    proposal = await client.post(
        "/api/source-config-proposals",
        json={
            "source_config_version_id": config["id"],
            "probe_run_ids": [probe.json()["id"]],
            "model_version": "pi-faux-v1",
            "prompt_version": "source-config-proposal-v1",
            "max_tokens": 200,
            "max_cost_cents": 2,
        },
    )

    assert probe.status_code == 201
    assert proposal.status_code == 201
    assert proposal.json()["evidence_refs"][0]["id"] == probe.json()["id"]
    assert proposal.json()["status"] == "unknown"
    assert proposal.json()["proposed_changes"] == {}
