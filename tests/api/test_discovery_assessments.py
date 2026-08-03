"""Evidence-cited assessments and operator-promoted Need Hypotheses."""

from datetime import UTC, datetime

from tests.api.test_discovery_objectives import objective_payload
from tests.factories import create_source


async def _objective(client, db):
    source = await create_source(db)
    created = await client.post("/api/discovery-objectives", json=objective_payload(source.id))
    return created.json()


async def _accepted_signal(client):
    signal = await client.post(
        "/api/external-signals",
        json={
            "source_label": "Public discussion",
            "source_uri": "https://example.com/discussion/42",
            "original_material": "I reconcile reports manually each Friday.",
            "observed_at": datetime.now(UTC).isoformat(),
            "observation": "A repeated manual reconciliation workaround is described.",
        },
    )
    await client.post(
        f"/api/external-signals/{signal.json()['id']}/triage",
        json={"status": "accepted", "reason": "Original context supports review."},
    )
    return signal.json()


async def test_assessment_requires_citations_and_workspace_exposes_its_judgement(client, db):
    objective = await _objective(client, db)
    signal = await _accepted_signal(client)

    rejected = await client.post(
        f"/api/discovery-objectives/{objective['id']}/assessments",
        json={"kind": "support", "statement": "A claim without evidence.", "evidence_ids": []},
    )
    created = await client.post(
        f"/api/discovery-objectives/{objective['id']}/assessments",
        json={
            "kind": "support",
            "statement": "The operator reports a repeated manual workaround.",
            "evidence_ids": [signal["id"]],
            "unknowns": ["How common this is across independent operators"],
            "recommendation": "Seek counterevidence from an automated workflow.",
        },
    )
    workspace = await client.get(f"/api/discovery-objectives/{objective['id']}/workspace")

    assert rejected.status_code == 422
    assert created.status_code == 201
    assert created.json()["version"] == 1
    assert workspace.json()["assessments"][0]["evidence_ids"] == [signal["id"]]


async def test_need_hypothesis_rejects_uncited_or_non_supporting_assessments(client, db):
    objective = await _objective(client, db)
    signal = await _accepted_signal(client)
    counter = await client.post(
        f"/api/discovery-objectives/{objective['id']}/assessments",
        json={
            "kind": "counterevidence",
            "statement": "One alternative works.",
            "evidence_ids": [signal["id"]],
        },
    )

    rejected = await client.post(
        f"/api/discovery-objectives/{objective['id']}/need-hypotheses",
        json={
            "title": "Manual reconciliation cost",
            "target_actor": "operators",
            "context": "weekly reporting",
            "problem": "manual reconciliation consumes time",
            "desired_outcome": "reconcile without repeated manual work",
            "next_validation_action": "find another independent operator",
            "support_assessment_ids": [counter.json()["id"]],
        },
    )

    assert rejected.status_code == 422
    assert "support" in rejected.json()["detail"].lower()


async def test_operator_can_explicitly_promote_supported_hypothesis_without_auto_creation(
    client, db
):
    objective = await _objective(client, db)
    signal = await _accepted_signal(client)
    support = await client.post(
        f"/api/discovery-objectives/{objective['id']}/assessments",
        json={
            "kind": "support",
            "statement": "A repeated cost is described.",
            "evidence_ids": [signal["id"]],
        },
    )
    hypothesis = await client.post(
        f"/api/discovery-objectives/{objective['id']}/need-hypotheses",
        json={
            "title": "Manual reconciliation cost",
            "target_actor": "operators",
            "context": "weekly reporting",
            "problem": "manual reconciliation consumes time",
            "desired_outcome": "reconcile without repeated manual work",
            "next_validation_action": "find another independent operator",
            "support_assessment_ids": [support.json()["id"]],
        },
    )
    before = await client.get("/api/need-issues")
    promoted = await client.post(
        f"/api/discovery-objectives/{objective['id']}/need-hypotheses/{hypothesis.json()['id']}/promote",
        json={"operator": "owner"},
    )

    assert before.json()["total"] == 0
    assert hypothesis.status_code == 201
    assert hypothesis.json()["status"] == "draft"
    assert promoted.status_code == 201
    assert promoted.json()["status"] == "captured"
