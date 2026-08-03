"""Public API contracts for the first Discovery Objective workspace."""

import uuid

from tests.factories import create_source


def objective_payload(source_id: uuid.UUID) -> dict:
    return {
        "title": "Independent operator incident recovery",
        "question": "What recurring recovery cost do independent operators describe?",
        "resource_stop_conditions": ["No more than 12 requests"],
        "evidence_stop_conditions": ["At least two independent sources"],
        "decision_stop_conditions": ["Promote, rewrite, abandon, or block"],
        "initial_boundary": {
            "approved_source_ids": [str(source_id)],
            "tool_allowlist": ["github_issue_collection"],
            "request_limit": 12,
            "time_budget_minutes": 30,
            "cost_budget_cents": 0,
        },
    }


async def test_create_objective_creates_an_immutable_initial_collection_boundary(client, db):
    source = await create_source(db)

    response = await client.post("/api/discovery-objectives", json=objective_payload(source.id))

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "active"
    assert body["question"] == "What recurring recovery cost do independent operators describe?"
    assert body["current_boundary"]["version"] == 1
    assert body["current_boundary"]["approved_source_ids"] == [str(source.id)]
    assert body["current_boundary"]["request_limit"] == 12


async def test_objective_workspace_returns_the_objective_and_its_current_boundary(client, db):
    source = await create_source(db)
    created = await client.post("/api/discovery-objectives", json=objective_payload(source.id))

    response = await client.get(f"/api/discovery-objectives/{created.json()['id']}/workspace")

    assert response.status_code == 200
    body = response.json()
    assert body["objective"]["id"] == created.json()["id"]
    assert body["current_boundary"]["version"] == 1
    assert body["plans"] == []
    assert body["assessments"] == []


async def test_objective_rejects_an_initial_boundary_that_names_an_unknown_source(client):
    response = await client.post("/api/discovery-objectives", json=objective_payload(uuid.uuid4()))

    assert response.status_code == 422
    assert "approved source" in response.json()["detail"].lower()


async def test_approval_request_pauses_objective_until_operator_decides(client, db):
    source = await create_source(db)
    created = await client.post("/api/discovery-objectives", json=objective_payload(source.id))
    objective_id = created.json()["id"]

    approval = await client.post(
        f"/api/discovery-objectives/{objective_id}/approvals",
        json={
            "request_type": "new_source",
            "reason": "A second independent source is required to test repetition.",
            "requested_boundary_patch": {"approved_source_ids": [str(source.id)]},
        },
    )
    workspace = await client.get(f"/api/discovery-objectives/{objective_id}/workspace")

    assert approval.status_code == 201
    assert approval.json()["status"] == "pending"
    assert workspace.json()["objective"]["status"] == "pending_approval"
    assert workspace.json()["pending_approvals"][0]["id"] == approval.json()["id"]


async def test_approving_request_versions_boundary_and_restores_active_objective(client, db):
    source = await create_source(db)
    second_source = await create_source(db, name="Second Source", url="https://example.com/second.xml")
    created = await client.post("/api/discovery-objectives", json=objective_payload(source.id))
    objective_id = created.json()["id"]
    approval = await client.post(
        f"/api/discovery-objectives/{objective_id}/approvals",
        json={
            "request_type": "new_source",
            "reason": "A second independent source is required.",
            "requested_boundary_patch": {"approved_source_ids": [str(second_source.id)]},
        },
    )

    decided = await client.post(
        f"/api/discovery-objectives/{objective_id}/approvals/{approval.json()['id']}/approve",
        json={"operator": "owner", "reason": "Approve one independent public source."},
    )
    workspace = await client.get(f"/api/discovery-objectives/{objective_id}/workspace")

    assert decided.status_code == 200
    assert decided.json()["status"] == "approved"
    assert workspace.json()["objective"]["status"] == "active"
    assert workspace.json()["current_boundary"]["version"] == 2
    assert workspace.json()["current_boundary"]["approved_source_ids"] == [str(second_source.id)]
    assert workspace.json()["boundary_revisions"][0]["approval_id"] == approval.json()["id"]


async def test_blocked_objective_can_only_reactivate_through_material_boundary_revision(client, db):
    source = await create_source(db)
    created = await client.post("/api/discovery-objectives", json=objective_payload(source.id))
    objective_id = created.json()["id"]

    blocked = await client.post(
        f"/api/discovery-objectives/{objective_id}/block",
        json={"reason": "The approved source is exhausted and cannot answer the question."},
    )
    no_change = await client.post(
        f"/api/discovery-objectives/{objective_id}/boundary-revisions",
        json={"operator": "owner", "reason": "Try again", "boundary_patch": {}},
    )
    revised = await client.post(
        f"/api/discovery-objectives/{objective_id}/boundary-revisions",
        json={
            "operator": "owner",
            "reason": "Grant a larger request budget for a new bounded pass.",
            "boundary_patch": {"request_limit": 24},
        },
    )

    assert blocked.status_code == 200
    assert blocked.json()["status"] == "blocked"
    assert no_change.status_code == 422
    assert revised.status_code == 201
    assert revised.json()["boundary_version"] == 2
    objective = await client.get(f"/api/discovery-objectives/{objective_id}")
    assert objective.json()["status"] == "active"
