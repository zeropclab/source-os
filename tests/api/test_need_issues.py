"""Tests for the evidence-backed Need Issue workflow."""

from datetime import UTC, datetime


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
            "unknowns": ["How many clinics already use confirmation automation"],
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

    counter = await client.post(
        f"/api/need-issues/{need_id}/evidence",
        json={
            "reference_type": "interview_note",
            "reference_uri": "notes://clinic-counterexample/1",
            "role": "counter",
            "excerpt": "One clinic already has automated confirmations.",
        },
    )
    challenge = await client.post(
        f"/api/need-issues/{need_id}/challenges",
        json={
            "basis": "The workflow may be solved by existing scheduling software.",
            "unknowns": ["How many clinics lack automation"],
            "falsification_condition": "Two target clinics use automation without this problem.",
            "smallest_next_action": "Interview one clinic with scheduling software.",
            "assessment": "insufficient-evidence",
        },
    )
    assert counter.status_code == 201
    assert challenge.status_code == 201

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


async def test_need_issue_preserves_signal_provenance_counterevidence_and_definition_history(
    client,
):
    signal = await client.post(
        "/api/external-signals",
        json={
            "source_label": "Public discussion",
            "source_uri": "https://example.com/discussions/42",
            "original_material": "I export two reports and reconcile them by hand.",
            "observed_at": datetime.now(UTC).isoformat(),
            "observation": "The operator reports a repeated manual reconciliation workaround.",
        },
    )
    assert signal.status_code == 201

    created = await client.post(
        "/api/need-issues",
        json={
            "title": "Operators reconcile reports manually",
            "target_actor": "small business operators",
            "context": "when closing a monthly reporting cycle",
            "problem": "they compare exports manually to find mismatches",
            "desired_outcome": "identify mismatches without repeated manual comparison",
            "workaround": "export both reports and compare rows manually",
            "unknowns": ["Whether this happens across independent businesses"],
            "next_validation_action": "collect a counterexample from a business using automation",
        },
    )
    assert created.status_code == 201
    need_id = created.json()["id"]

    supporting = await client.post(
        f"/api/need-issues/{need_id}/evidence",
        json={
            "reference_type": "external_signal",
            "reference_uri": "https://example.com/discussions/42",
            "external_signal_id": signal.json()["id"],
            "role": "supporting",
            "excerpt": "I export two reports and reconcile them by hand.",
        },
    )
    counter = await client.post(
        f"/api/need-issues/{need_id}/evidence",
        json={
            "reference_type": "interview_note",
            "reference_uri": "obsidian://counterexample/1",
            "role": "counter",
            "excerpt": "Our accounting software reconciles this automatically.",
        },
    )
    assert supporting.status_code == 201
    assert supporting.json()["external_signal_id"] == signal.json()["id"]
    assert counter.status_code == 201

    updated = await client.patch(
        f"/api/need-issues/{need_id}",
        json={
            "problem": "they repeatedly compare exports manually to locate mismatches",
            "change_reason": "Original wording did not preserve the repeated behavior.",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["definition_version"] == 2

    versions = await client.get(f"/api/need-issues/{need_id}/versions")
    assert versions.status_code == 200
    assert [version["version"] for version in versions.json()["items"]] == [1, 2]
    assert versions.json()["items"][1]["change_reason"] == (
        "Original wording did not preserve the repeated behavior."
    )


async def test_need_issue_requires_reason_and_new_evidence_to_reopen_from_dormant_or_rejected(
    client,
):
    created = await client.post(
        "/api/need-issues",
        json={
            "title": "Dispatchers lose handoff context",
            "target_actor": "dispatchers",
            "context": "when a shift changes",
            "problem": "handoff notes live in disconnected channels",
            "desired_outcome": "start a shift with the current operational context",
            "unknowns": ["Whether this delays incidents"],
            "next_validation_action": "observe one live shift handoff",
        },
    )
    need_id = created.json()["id"]

    missing_reason = await client.post(
        f"/api/need-issues/{need_id}/transition", json={"status": "dormant"}
    )
    assert missing_reason.status_code == 422

    dormant = await client.post(
        f"/api/need-issues/{need_id}/transition",
        json={"status": "dormant", "reason": "No reachable operators this month."},
    )
    assert dormant.status_code == 200
    assert dormant.json()["status"] == "dormant"

    missing_new_evidence = await client.post(
        f"/api/need-issues/{need_id}/transition",
        json={"status": "captured", "reason": "A new contact is available."},
    )
    assert missing_new_evidence.status_code == 422

    reopened = await client.post(
        f"/api/need-issues/{need_id}/transition",
        json={
            "status": "captured",
            "reason": "A new contact is available.",
            "new_evidence": {
                "reference_type": "interview_note",
                "reference_uri": "obsidian://interview/dispatch-1",
                "role": "supporting",
                "excerpt": "The incoming dispatcher asks the same questions every shift.",
            },
        },
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "captured"

    events = await client.get(f"/api/need-issues/{need_id}/status-events")
    assert events.status_code == 200
    assert [event["reason"] for event in events.json()["items"]] == [
        "No reachable operators this month.",
        "A new contact is available.",
    ]


async def test_discovery_validation_gate_requires_counterevidence_unknowns_and_a_challenge(client):
    created = await client.post(
        "/api/need-issues",
        json={
            "title": "Operators repeatedly reconcile exports",
            "target_actor": "small business operators",
            "context": "during a monthly close",
            "problem": "they compare exports manually to find mismatches",
            "desired_outcome": "find mismatches without manual comparison",
            "unknowns": ["Whether this is independently repeated"],
            "next_validation_action": "interview an operator about a recent close",
        },
    )
    need_id = created.json()["id"]

    supporting = await client.post(
        f"/api/need-issues/{need_id}/evidence",
        json={
            "reference_type": "interview_note",
            "reference_uri": "obsidian://interview/1",
            "role": "supporting",
        },
    )
    assert supporting.status_code == 201

    blocked = await client.post(
        f"/api/need-issues/{need_id}/transition",
        json={"status": "discovery-validated"},
    )
    assert blocked.status_code == 409
    assert (
        blocked.json()["detail"]
        == "Discovery validation gate is incomplete: counter evidence, challenge"
    )

    counter = await client.post(
        f"/api/need-issues/{need_id}/evidence",
        json={
            "reference_type": "counterexample",
            "reference_uri": "obsidian://counter/1",
            "role": "counter",
        },
    )
    challenge = await client.post(
        f"/api/need-issues/{need_id}/challenges",
        json={
            "basis": "One operator may not represent an independent recurring problem.",
            "unknowns": ["How often the workaround occurs"],
            "falsification_condition": "Two independent operators report no manual reconciliation.",
            "smallest_next_action": (
                "Ask one independent operator for a recent reconciliation example."
            ),
            "assessment": "insufficient-evidence",
        },
    )
    assert counter.status_code == 201
    assert challenge.status_code == 201

    validated = await client.post(
        f"/api/need-issues/{need_id}/transition",
        json={"status": "discovery-validated", "reason": "Gate requirements are now reviewable."},
    )
    assert validated.status_code == 200


async def test_operator_override_of_an_incomplete_discovery_gate_is_explicitly_audited(client):
    created = await client.post(
        "/api/need-issues",
        json={
            "title": "A constrained pilot needs a decision",
            "target_actor": "pilot operators",
            "context": "during a paid pilot",
            "problem": "the pilot workflow is blocked",
            "desired_outcome": "decide whether to test the workaround",
            "unknowns": ["Whether the pilot is representative"],
            "next_validation_action": "run a constrained pilot observation",
        },
    )
    need_id = created.json()["id"]

    overridden = await client.post(
        f"/api/need-issues/{need_id}/transition",
        json={
            "status": "discovery-validated",
            "override_gate": True,
            "reason": "A time-bounded paid pilot already supplies the next reality contact.",
        },
    )
    assert overridden.status_code == 200
    events = await client.get(f"/api/need-issues/{need_id}/status-events")
    assert events.json()["items"][-1]["reason"].startswith("OVERRIDE: ")
