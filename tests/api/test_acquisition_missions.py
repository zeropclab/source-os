"""Behavior tests for bounded Acquisition Mission drafts."""

import pytest

from tests.factories import create_source


async def _create_source_config(client, source_id, *, query_terms=None, access_mode="public"):
    response = await client.post(
        f"/api/sources/{source_id}/config-versions",
        json={
            "access_mode": access_mode,
            "query_scope": {"query_terms": query_terms or ["invoice mismatch"]},
            "request_policy": {"request_limit": 2, "timeout_seconds": 10},
            "pagination_context_rules": {
                "page_limit": 1,
                "include_replies": True,
                "require_parent_context": True,
            },
            "extraction_settings": {
                "parser": "github_issue",
                "parser_version": "v1",
                "content_fields": ["title", "body", "comments"],
            },
        },
    )
    assert response.status_code == 201
    return response.json()


async def test_operator_can_create_and_retrieve_a_bounded_draft_mission(client, db):
    source = await create_source(
        db,
        name="GitHub public issues",
        platform="github",
        source_type="issues",
        url="https://github.com/example/public-project/issues",
    )
    pinned_config = await _create_source_config(client, source.id)
    payload = {
        "reality_question": (
            "Do Indonesian freelancers incur observable reconciliation costs "
            "when receiving cross-border payments?"
        ),
        "mission_type": "targeted_evidence",
        "source_id": str(source.id),
        "source_config_version_id": pinned_config["id"],
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
    assert created_data["source_config_version_id"] == pinned_config["id"]
    assert created_data["source_config_version"] == pinned_config

    newer_config = await _create_source_config(
        client,
        source.id,
        query_terms=["invoice mismatch", "transfer fee"],
    )
    assert newer_config["version"] == 2

    retrieved = await client.get(f"/api/acquisition-missions/{created_data['id']}")

    assert retrieved.status_code == 200
    assert retrieved.json() == created_data
    assert retrieved.json()["source_config_version"]["version"] == 1


@pytest.mark.parametrize("access_mode", ["blocked", "unsupported"])
async def test_operator_cannot_pin_a_mission_to_an_unusable_config(client, db, access_mode):
    source = await create_source(
        db,
        name="Unavailable source",
        platform="github",
        source_type="issues",
        url="https://github.com/example/public-project/issues",
    )
    config = await _create_source_config(client, source.id, access_mode=access_mode)

    response = await client.post(
        "/api/acquisition-missions",
        json={
            "reality_question": "What observable cost does reconciliation create?",
            "mission_type": "targeted_evidence",
            "source_id": str(source.id),
            "source_config_version_id": config["id"],
            "regions": ["ID"],
            "languages": ["id"],
            "target_audience": "freelancers",
            "query_seeds": ["invoice mismatch"],
            "time_budget_minutes": 45,
            "item_limit": 50,
            "cost_budget_cents": 2000,
            "stop_conditions": ["Collect 12 independent observations"],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        f"Source configuration version cannot run a mission while access mode is {access_mode}"
    )


async def test_operator_cannot_pin_a_config_from_a_different_source(client, db):
    selected_source = await create_source(
        db,
        name="Selected source",
        platform="github",
        source_type="issues",
        url="https://github.com/example/selected/issues",
    )
    other_source = await create_source(
        db,
        name="Other source",
        platform="github",
        source_type="issues",
        url="https://github.com/example/other/issues",
    )
    other_config = await _create_source_config(client, other_source.id)

    response = await client.post(
        "/api/acquisition-missions",
        json={
            "reality_question": "What observable cost does reconciliation create?",
            "mission_type": "targeted_evidence",
            "source_id": str(selected_source.id),
            "source_config_version_id": other_config["id"],
            "regions": ["ID"],
            "languages": ["id"],
            "target_audience": "freelancers",
            "query_seeds": ["invoice mismatch"],
            "time_budget_minutes": 45,
            "item_limit": 50,
            "cost_budget_cents": 2000,
            "stop_conditions": ["Collect 12 independent observations"],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Source configuration version is missing or does not belong to the selected source"
    )


async def test_operator_must_select_a_source_config_version(client, db):
    source = await create_source(
        db,
        name="Selected source",
        platform="github",
        source_type="issues",
        url="https://github.com/example/selected/issues",
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
            "stop_conditions": ["Collect 12 independent observations"],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "source_config_version_id"]


async def test_operator_cannot_create_a_mission_without_a_stop_condition(client, db):
    source = await create_source(
        db,
        name="GitHub public issues",
        platform="github",
        source_type="issues",
        url="https://github.com/example/public-project/issues",
    )
    config = await _create_source_config(client, source.id)

    response = await client.post(
        "/api/acquisition-missions",
        json={
            "reality_question": "What observable cost does reconciliation create?",
            "mission_type": "targeted_evidence",
            "source_id": str(source.id),
            "source_config_version_id": config["id"],
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
    config = await _create_source_config(client, source.id)

    response = await client.post(
        "/api/acquisition-missions",
        json={
            "reality_question": "What observable cost does reconciliation create?",
            "mission_type": "targeted_evidence",
            "source_id": str(source.id),
            "source_config_version_id": config["id"],
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
