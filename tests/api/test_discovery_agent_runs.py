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
    assert created.json()["input_context"]["objective"]["status"] == "active"
    assert created.json()["input_context"]["boundary"]["version"] == 1
    assert rejected.status_code == 409


async def test_objective_agent_run_is_rejected_at_execution_when_boundary_is_no_longer_active(
    client, db
):
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
    run = await client.post(
        f"/api/discovery-objectives/{objective.json()['id']}/agent-runs",
        json={
            "evidence_signal_ids": [signal.json()["id"]],
            "task_instruction": "Return a structured assessment proposal only.",
            "idempotency_key": "objective-agent-run-execute-v1",
            "model_version": "pi-faux-v1",
            "prompt_version": "discovery-assessment-v1",
            "max_tool_calls": 1,
            "max_tokens": 500,
            "max_cost_cents": 0,
        },
    )
    await client.post(
        f"/api/discovery-objectives/{objective.json()['id']}/block",
        json={"reason": "No approved next action remains."},
    )

    execution = await client.post(f"/api/agent-runs/{run.json()['id']}/execute")

    assert execution.status_code == 409
    assert execution.json()["detail"] == "Discovery Agent run boundary is no longer active"


async def test_objective_agent_run_returns_a_structured_assessment_proposal(client, db):
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
    run = await client.post(
        f"/api/discovery-objectives/{objective.json()['id']}/agent-runs",
        json={
            "evidence_signal_ids": [signal.json()["id"]],
            "task_instruction": "Return a structured assessment proposal only.",
            "idempotency_key": "objective-agent-run-proposal-v1",
            "model_version": "pi-faux-v1",
            "prompt_version": "discovery-assessment-v1",
            "max_tool_calls": 1,
            "max_tokens": 500,
            "max_cost_cents": 0,
        },
    )

    completed = await client.post(f"/api/agent-runs/{run.json()['id']}/execute")

    assert completed.status_code == 200
    proposal = completed.json()["output"]["proposal"]
    assert proposal["contract"] == "discovery_assessment_proposal.v1"
    assert proposal["kind"] == "unknown"
    assert proposal["evidence_ids"] == [signal.json()["id"]]


async def test_plan_bound_agent_run_can_only_return_a_structured_revision_proposal(client, db):
    source = await create_source(db)
    objective = await client.post("/api/discovery-objectives", json=objective_payload(source.id))
    plan = await client.post(
        f"/api/discovery-objectives/{objective.json()['id']}/plans",
        json={
            "question": "Which reconciliation costs recur?",
            "selected_source_ids": [str(source.id)],
            "counterevidence_target": "A sufficient existing workaround.",
            "request_budget": 1,
            "time_budget_minutes": 5,
            "cost_budget_cents": 0,
        },
    )
    signal = await client.post(
        "/api/external-signals",
        json={
            "source_label": "Public discussion",
            "original_material": "I reconcile reports each Friday.",
            "observed_at": datetime.now(UTC).isoformat(),
            "observation": "A manual workaround is reported.",
        },
    )
    run = await client.post(
        f"/api/discovery-objectives/{objective.json()['id']}/agent-runs",
        json={
            "evidence_signal_ids": [signal.json()["id"]],
            "task_instruction": "Propose a plan revision only.",
            "idempotency_key": "objective-agent-plan-revision-v1",
            "model_version": "pi-faux-v1",
            "prompt_version": "discovery-plan-revision-v1",
            "max_tool_calls": 1,
            "max_tokens": 500,
            "max_cost_cents": 0,
            "max_time_minutes": 5,
            "acquisition_plan_id": plan.json()["id"],
            "proposal_type": "plan_revision",
        },
    )

    completed = await client.post(f"/api/agent-runs/{run.json()['id']}/execute")

    assert run.status_code == 201
    assert run.json()["acquisition_plan_id"] == plan.json()["id"]
    assert run.json()["input_context"]["plan"]["id"] == plan.json()["id"]
    assert completed.json()["output"]["proposal"] == {
        "contract": "acquisition_plan_revision_proposal.v1",
        "predecessor_plan_id": plan.json()["id"],
        "proposed_delta": {},
        "reason": "Pi output cannot support a Plan Revision proposal yet.",
        "coverage_gaps": ["Pi output did not satisfy the plan revision contract."],
        "status": "unknown",
    }
