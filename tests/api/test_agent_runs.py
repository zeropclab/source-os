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
        "model_version": "deterministic-fake-v1",
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
    assert run["tool_allowlist"] == ["retrieve_evidence", "find_counterevidence"]

    completed = await client.post(f"/api/agent-runs/{run['id']}/execute")
    assert completed.status_code == 200
    output = completed.json()["output"]
    assert completed.json()["status"] == "completed"
    assert completed.json()["usage"]["tool_calls"] <= 2
    assert completed.json()["usage"]["cost_cents"] <= 5
    assert output["kind"] == "need_issue_proposal"
    assert set(output["citations"]) == {supporting, counter}
    assert output["proposed_status"] == "captured"
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
            "model_version": "deterministic-fake-v1",
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
