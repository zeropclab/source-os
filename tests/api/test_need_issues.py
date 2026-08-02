"""Tests for the evidence-backed Need Issue workflow."""


async def test_create_need_issue_as_unvalidated_internal_record(client):
    response = await client.post(
        "/api/need-issues",
        json={
            "title": "Freelance translators lose track of client terminology",
            "target_actor": "independent translators",
            "context": "when revising recurring client work",
            "problem": "terminology decisions are scattered across documents and chats",
            "desired_outcome": "reuse approved client terminology without manual searching",
            "next_validation_action": "interview five translators who handle repeat clients",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "captured"
    assert body["evidence_count"] == 0
    assert body["id"]


async def test_need_issue_cannot_skip_evidence_gate_before_feature_definition(client):
    created = await client.post(
        "/api/need-issues",
        json={
            "title": "Field technicians repeat offline checklists",
            "target_actor": "field service technicians",
            "context": "at sites with unreliable connectivity",
            "problem": "checklists are re-entered after reconnecting",
            "desired_outcome": "complete one checklist that synchronizes safely later",
            "next_validation_action": "collect two concrete workflow accounts",
        },
    )
    need_id = created.json()["id"]

    response = await client.post(
        f"/api/need-issues/{need_id}/transition",
        json={"status": "feature-defined"},
    )

    assert response.status_code == 409
    assert "discovery-validated" in response.json()["detail"]


async def test_feature_definition_requires_validated_need_and_tracking_plan(client):
    created = await client.post(
        "/api/need-issues",
        json={
            "title": "Clinic coordinators chase appointment confirmations",
            "target_actor": "small clinic coordinators",
            "context": "one day before an appointment",
            "problem": "they manually chase confirmations through multiple channels",
            "desired_outcome": "know which appointments need follow-up",
            "next_validation_action": "test the workflow with two clinics",
        },
    )
    need_id = created.json()["id"]

    evidence = await client.post(
        f"/api/need-issues/{need_id}/evidence",
        json={
            "reference_type": "external_signal",
            "reference_uri": "https://example.com/comments/123",
            "role": "supporting",
            "excerpt": "I spend an hour every evening chasing confirmations.",
        },
    )
    assert evidence.status_code == 201

    validated = await client.post(
        f"/api/need-issues/{need_id}/transition",
        json={"status": "discovery-validated"},
    )
    assert validated.status_code == 200

    feature = await client.post(
        f"/api/need-issues/{need_id}/features",
        json={
            "title": "Confirmation follow-up board",
            "user_task": "Review tomorrow's appointments and send one follow-up",
            "scope": "Manual import and a status board only",
            "acceptance_criteria": [
                "Shows unconfirmed appointments",
                "Records a follow-up timestamp",
            ],
            "tracking_events": ["follow_up_board_viewed", "follow_up_sent"],
            "tracking_properties": ["clinic_id", "appointment_count"],
            "success_metric": (
                "At least 60% of pilot coordinators send a follow-up in the first week"
            ),
            "negative_metric": "More than 20% abandon the board before selecting an appointment",
        },
    )

    assert feature.status_code == 201
    body = feature.json()
    assert body["need_issue_id"] == need_id
    assert body["status"] == "defined"

