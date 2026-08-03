"""Plans must stay inside their Objective's approved collection boundary."""

from tests.api.test_acquisition_missions import _create_source_config, _mission_payload
from tests.api.test_discovery_objectives import objective_payload
from tests.factories import create_source


async def create_objective(client, source_id):
    response = await client.post("/api/discovery-objectives", json=objective_payload(source_id))
    assert response.status_code == 201
    return response.json()


async def test_plan_pins_current_boundary_and_can_expose_its_mission_chain(client, db):
    source = await create_source(db)
    objective = await create_objective(client, source.id)

    plan = await client.post(
        f"/api/discovery-objectives/{objective['id']}/plans",
        json={
            "question": "Which recovery costs recur across independent operator reports?",
            "selected_source_ids": [str(source.id)],
            "counterevidence_target": "Reports that the existing workaround is sufficient.",
            "request_budget": 8,
            "time_budget_minutes": 20,
            "cost_budget_cents": 0,
        },
    )
    workspace = await client.get(f"/api/discovery-objectives/{objective['id']}/workspace")

    assert plan.status_code == 201
    assert plan.json()["version"] == 1
    assert plan.json()["boundary_version"] == 1
    assert workspace.json()["plans"][0]["id"] == plan.json()["id"]
    assert workspace.json()["plans"][0]["missions"] == []


async def test_plan_rejects_sources_or_budgets_outside_current_boundary(client, db):
    source = await create_source(db)
    outside_source = await create_source(db, name="Outside", url="https://example.com/outside.xml")
    objective = await create_objective(client, source.id)

    rejected = await client.post(
        f"/api/discovery-objectives/{objective['id']}/plans",
        json={
            "question": "Can this source answer the objective?",
            "selected_source_ids": [str(outside_source.id)],
            "counterevidence_target": "A contrary observation.",
            "request_budget": 13,
            "time_budget_minutes": 20,
            "cost_budget_cents": 0,
        },
    )

    assert rejected.status_code == 422
    assert "boundary" in rejected.json()["detail"].lower()


async def test_plan_revision_retains_predecessor_and_reason(client, db):
    source = await create_source(db)
    objective = await create_objective(client, source.id)
    initial = await client.post(
        f"/api/discovery-objectives/{objective['id']}/plans",
        json={
            "question": "What recovery costs recur?",
            "selected_source_ids": [str(source.id)],
            "counterevidence_target": "No recurring recovery cost.",
            "request_budget": 4,
            "time_budget_minutes": 10,
            "cost_budget_cents": 0,
        },
    )

    revised = await client.post(
        f"/api/discovery-objectives/{objective['id']}/plans",
        json={
            "question": "What recovery costs recur across distinct threads?",
            "selected_source_ids": [str(source.id)],
            "counterevidence_target": "A workaround removes the cost.",
            "request_budget": 6,
            "time_budget_minutes": 15,
            "cost_budget_cents": 0,
            "predecessor_plan_id": initial.json()["id"],
            "revision_reason": "Coverage gap: the first plan had only one thread.",
            "revision_delta": {"source_independence_required": True},
        },
    )

    assert revised.status_code == 201
    assert revised.json()["version"] == 2
    assert revised.json()["predecessor_plan_id"] == initial.json()["id"]
    assert revised.json()["revision"]["reason"] == (
        "Coverage gap: the first plan had only one thread."
    )


async def test_linked_mission_must_keep_using_a_plan_allowed_by_current_boundary(client, db):
    source = await create_source(db)
    objective = await create_objective(client, source.id)
    plan = await client.post(
        f"/api/discovery-objectives/{objective['id']}/plans",
        json={
            "question": "What recurring recovery costs appear?",
            "selected_source_ids": [str(source.id)],
            "counterevidence_target": "No recurring cost appears.",
            "request_budget": 8,
            "time_budget_minutes": 20,
            "cost_budget_cents": 0,
        },
    )
    config = await _create_source_config(client, source.id)

    linked = await client.post(
        "/api/acquisition-missions",
        json=_mission_payload(
            source.id,
            config["id"],
            acquisition_plan_id=plan.json()["id"],
            cost_budget_cents=0,
        ),
    )
    queued = await client.post(
        f"/api/acquisition-missions/{linked.json()['id']}/queued-runs",
        json={"execution_mode": "fixture"},
    )
    workspace = await client.get(f"/api/discovery-objectives/{objective['id']}/workspace")
    approval = await client.post(
        f"/api/discovery-objectives/{objective['id']}/approvals",
        json={
            "request_type": "budget_change",
            "reason": "A small additional allowance is required.",
            "requested_boundary_patch": {"request_limit": 16},
        },
    )
    await client.post(
        f"/api/discovery-objectives/{objective['id']}/approvals/{approval.json()['id']}/approve",
        json={"operator": "owner", "reason": "Approved."},
    )
    stale = await client.post(
        "/api/acquisition-missions",
        json=_mission_payload(
            source.id,
            config["id"],
            acquisition_plan_id=plan.json()["id"],
            cost_budget_cents=0,
        ),
    )
    stale_run = await client.post(
        f"/api/acquisition-missions/{linked.json()['id']}/queued-runs",
        json={"execution_mode": "fixture"},
    )

    assert linked.status_code == 201
    assert queued.status_code == 201
    assert linked.json()["acquisition_plan_id"] == plan.json()["id"]
    assert (
        workspace.json()["plans"][0]["mission_runs"][linked.json()["id"]][0]["id"]
        == queued.json()["id"]
    )
    assert stale.status_code == 409
    assert stale_run.status_code == 409
    assert (
        stale_run.json()["detail"] == "Plan is no longer permitted by the current approved boundary"
    )
