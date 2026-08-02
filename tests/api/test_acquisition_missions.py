"""Behavior tests for bounded Acquisition Mission drafts."""

from tests.factories import create_source


async def test_operator_can_create_and_retrieve_a_bounded_draft_mission(client, db):
    source = await create_source(
        db,
        name="GitHub public issues",
        platform="github",
        source_type="issues",
        url="https://github.com/example/public-project/issues",
    )
    payload = {
        "reality_question": (
            "Do Indonesian freelancers incur observable reconciliation costs "
            "when receiving cross-border payments?"
        ),
        "mission_type": "targeted_evidence",
        "source_id": str(source.id),
        "regions": ["ID"],
        "languages": ["id"],
        "target_audience": "freelancers and micro-exporters",
        "query_seeds": ["invoice mismatch", "biaya transfer"],
        "time_budget_minutes": 45,
        "item_limit": 50,
        "cost_budget_cents": 2000,
        "stop_conditions": ["Collect 12 independent observations with behavior or cost"],
    }

    created = await client.post("/api/acquisition-missions", json=payload)

    assert created.status_code == 201
    created_data = created.json()
    assert created_data["status"] == "draft"
    assert created_data["reality_question"] == payload["reality_question"]
    assert created_data["time_budget_minutes"] == 45
    assert created_data["item_limit"] == 50
    assert created_data["cost_budget_cents"] == 2000
    assert created_data["stop_conditions"] == payload["stop_conditions"]

    retrieved = await client.get(f"/api/acquisition-missions/{created_data['id']}")

    assert retrieved.status_code == 200
    assert retrieved.json() == created_data


async def test_operator_cannot_create_a_mission_without_a_stop_condition(client, db):
    source = await create_source(
        db,
        name="GitHub public issues",
        platform="github",
        source_type="issues",
        url="https://github.com/example/public-project/issues",
    )

    response = await client.post(
        "/api/acquisition-missions",
        json={
            "reality_question": "What observable cost does reconciliation create?",
            "mission_type": "targeted_evidence",
            "source_id": str(source.id),
            "regions": ["ID"],
            "languages": ["id"],
            "target_audience": "freelancers",
            "query_seeds": ["invoice mismatch"],
            "time_budget_minutes": 45,
            "item_limit": 50,
            "cost_budget_cents": 2000,
            "stop_conditions": [],
        },
    )

    assert response.status_code == 422


async def test_operator_cannot_use_blank_text_as_a_stop_condition(client, db):
    source = await create_source(
        db,
        name="GitHub public issues",
        platform="github",
        source_type="issues",
        url="https://github.com/example/public-project/issues",
    )

    response = await client.post(
        "/api/acquisition-missions",
        json={
            "reality_question": "What observable cost does reconciliation create?",
            "mission_type": "targeted_evidence",
            "source_id": str(source.id),
            "regions": ["ID"],
            "languages": ["id"],
            "target_audience": "freelancers",
            "query_seeds": ["invoice mismatch"],
            "time_budget_minutes": 45,
            "item_limit": 50,
            "cost_budget_cents": 2000,
            "stop_conditions": ["   "],
        },
    )

    assert response.status_code == 422
