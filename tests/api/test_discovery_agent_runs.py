"""Objective-scoped Pi runs cannot exceed the active collection boundary."""

from datetime import UTC, datetime

from tests.api.test_discovery_objectives import objective_payload
from tests.factories import create_source


async def test_objective_agent_run_pins_boundary_and_rejects_blocked_objective(client, db):
    source = await create_source(db)
    objective = await client.post("/api/discovery-objectives", json=objective_payload(source.id))
    signal = await client.post(
        "/api/external-signals",
        json={
            "source_label": "Public discussion",
            "original_material": "I reconcile reports each Friday.",
            "observed_at": datetime.now(UTC).isoformat(),
            "observation": "A manual workaround is reported.",
        },
    )
    payload = {
        "evidence_signal_ids": [signal.json()["id"]],
        "task_instruction": "Return a structured assessment proposal only.",
        "idempotency_key": "objective-agent-run-v1",
        "model_version": "pi-faux-v1",
        "prompt_version": "discovery-assessment-v1",
        "max_tool_calls": 2,
        "max_tokens": 500,
        "max_cost_cents": 0,
    }

    created = await client.post(
        f"/api/discovery-objectives/{objective.json()['id']}/agent-runs", json=payload
    )
    await client.post(
        f"/api/discovery-objectives/{objective.json()['id']}/block",
        json={"reason": "No approved next action remains."},
    )
    rejected = await client.post(
        f"/api/discovery-objectives/{objective.json()['id']}/agent-runs",
        json={**payload, "idempotency_key": "blocked-run"},
    )

    assert created.status_code == 201
    assert created.json()["objective_id"] == objective.json()["id"]
    assert created.json()["boundary_version"] == 1
    assert created.json()["tool_allowlist"] == ["github_issue_collection"]
    assert rejected.status_code == 409
