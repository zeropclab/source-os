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
