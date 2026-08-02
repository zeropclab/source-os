"""Behavior tests for bounded, proposal-only Agent Runs."""

from datetime import UTC, datetime


async def _signal(client, material: str, observation: str) -> str:
    response = await client.post(
        "/api/external-signals",
        json={
            "source_label": "Fixed evidence bundle",
            "original_material": material,
            "observed_at": datetime.now(UTC).isoformat(),
            "observation": observation,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


async def test_agent_run_is_bounded_auditable_and_only_returns_a_cited_proposal(client):
    supporting = await _signal(
        client,
        "I export two reports and reconcile rows manually every Friday.",
        "A repeated manual reconciliation workaround was reported.",
    )
    counter = await _signal(
        client,
        "Our accounting platform already reconciles the two reports automatically.",
        "A competing explanation is that suitable automation already exists.",
    )
    payload = {
        "evidence_signal_ids": [supporting, counter],
        "task_instruction": "Draft one falsifiable need hypothesis from this bounded evidence.",
        "idempotency_key": "reconciliation-bundle-v1",
        "model_version": "pi-faux-v1",
        "prompt_version": "need-proposal-v1",
        "max_tool_calls": 2,
        "max_tokens": 500,
        "max_cost_cents": 5,
    }

    created = await client.post("/api/agent-runs", json=payload)
    duplicate = await client.post("/api/agent-runs", json=payload)

    assert created.status_code == 201
    assert duplicate.status_code == 200
    run = created.json()
    assert duplicate.json()["id"] == run["id"]
    assert run["status"] == "created"
    assert run["evidence_bundle_hash"]
    assert run["tool_allowlist"] == []

    retrieved = await client.get(f"/api/agent-runs/{run['id']}")
    assert retrieved.status_code == 200
    assert retrieved.json()["id"] == run["id"]
    assert retrieved.json()["evidence_bundle_hash"] == run["evidence_bundle_hash"]
    assert retrieved.json()["output"] is None

    completed = await client.post(f"/api/agent-runs/{run['id']}/execute")
    assert completed.status_code == 200
    output = completed.json()["output"]
    assert completed.json()["status"] == "completed"
    assert completed.json()["usage"]["tool_calls"] == 0
    assert completed.json()["usage"]["tokens"] >= 0
    assert completed.json()["usage"]["cost_cents"] == 0
    assert output["provider"] == "faux"
    assert set(output["citations"]) == {supporting, counter}
    assert output["cannot_conclude"]
    assert completed.json()["operator_changes"] == []

    reviewed = await client.post(
        f"/api/agent-runs/{run['id']}/operator-decisions",
        json={
            "decision": "modified",
            "reason": "Actor is not established by the cited material.",
            "changes": [{"field": "actor", "value": "unknown"}],
        },
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["operator_changes"][0]["decision"] == "modified"


async def test_cancelled_agent_run_never_executes_or_creates_a_business_effect(client):
    signal_id = await _signal(
        client,
        "I copy the same customer details between two spreadsheets.",
        "A manual data-copying workaround was reported.",
    )
    created = await client.post(
        "/api/agent-runs",
        json={
            "evidence_signal_ids": [signal_id],
            "task_instruction": "Find a competing explanation before proposing any need.",
            "idempotency_key": "cancel-before-execute-v1",
            "model_version": "pi-faux-v1",
            "prompt_version": "need-proposal-v1",
            "max_tool_calls": 1,
            "max_tokens": 200,
            "max_cost_cents": 2,
        },
    )
    run_id = created.json()["id"]

    cancelled = await client.post(f"/api/agent-runs/{run_id}/cancel")
    execution = await client.post(f"/api/agent-runs/{run_id}/execute")

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["output"] is None
    assert execution.status_code == 409
    assert execution.json()["detail"] == "Cancelled Agent Run cannot execute"


async def test_unconfigured_real_provider_records_auditable_failure(client):
    signal_id = await _signal(
        client,
        "I pay someone to reconcile two data exports every week.",
        "A recurring paid workaround was reported.",
    )
    created = await client.post(
        "/api/agent-runs",
        json={
            "evidence_signal_ids": [signal_id],
            "task_instruction": "Propose only; do not validate the need.",
            "idempotency_key": "unconfigured-real-provider-v1",
            "model_version": "openai/gpt-5-mini",
            "prompt_version": "need-proposal-v1",
            "max_tool_calls": 1,
            "max_tokens": 200,
            "max_cost_cents": 2,
        },
    )
    execution = await client.post(f"/api/agent-runs/{created.json()['id']}/execute")

    assert execution.status_code == 200
    assert execution.json()["status"] == "failed"
    assert execution.json()["output"] is None
    assert execution.json()["errors"][0]["stage"] == "runtime"
    assert "not configured" in execution.json()["errors"][0]["error"]
