"""Closing an Objective creates an immutable decision record with append-only outcomes."""

from tests.api.test_discovery_objectives import objective_payload
from tests.factories import create_source


async def test_close_objective_creates_decision_record_and_appends_outcome_feedback(client, db):
    source = await create_source(db)
    objective = await client.post("/api/discovery-objectives", json=objective_payload(source.id))
    record = await client.post(
        f"/api/discovery-objectives/{objective.json()['id']}/decision-records",
        json={
            "decision": "abandoned",
            "reason": "Counterevidence outweighs the available support.",
            "support_assessment_ids": [],
            "counter_assessment_ids": [],
            "unknowns": ["Whether a narrower segment experiences the cost"],
            "resource_usage": {"requests": 12, "minutes": 30, "cost_cents": 0},
        },
    )
    outcome = await client.post(
        f"/api/discovery-objectives/{objective.json()['id']}/decision-records/{record.json()['id']}/outcomes",
        json={
            "kind": "support",
            "reference": "tracking://product/42",
            "summary": "Later tracking is calibration input only.",
        },
    )

    assert record.status_code == 201
    assert record.json()["decision"] == "abandoned"
    assert outcome.status_code == 201
    assert outcome.json()["decision_record_id"] == record.json()["id"]

    workspace = await client.get(f"/api/discovery-objectives/{objective.json()['id']}/workspace")

    assert workspace.status_code == 200
    assert workspace.json()["decision_record"]["reason"] == (
        "Counterevidence outweighs the available support."
    )
    assert workspace.json()["decision_record"]["outcomes"] == [
        {
            "id": outcome.json()["id"],
            "decision_record_id": record.json()["id"],
            "kind": "support",
            "reference": "tracking://product/42",
            "summary": "Later tracking is calibration input only.",
            "created_at": outcome.json()["created_at"],
        }
    ]


async def test_decision_record_rejects_unknown_assessment_citations(client, db):
    source = await create_source(db)
    objective = await client.post("/api/discovery-objectives", json=objective_payload(source.id))

    response = await client.post(
        f"/api/discovery-objectives/{objective.json()['id']}/decision-records",
        json={
            "decision": "abandoned",
            "reason": "The question cannot be supported yet.",
            "support_assessment_ids": ["00000000-0000-0000-0000-000000000001"],
            "counter_assessment_ids": [],
            "unknowns": [],
            "resource_usage": {"requests": 0, "minutes": 0, "cost_cents": 0},
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Decision Record cites an assessment outside this objective"
