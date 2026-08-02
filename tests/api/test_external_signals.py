"""Tests for immutable manual reality signals and the evidence inbox."""


async def test_capture_manual_signal_preserves_observation_interpretation_and_provenance(client):
    response = await client.post(
        "/api/external-signals",
        json={
            "source_label": "Conversation with a freelance translator",
            "source_uri": "notes://field-interview/2026-08-02-translator",
            "original_material": (
                "I keep approved terminology in three places and still resend old terms."
            ),
            "observed_at": "2026-08-02T09:30:00Z",
            "observation": (
                "The translator described copying terminology across disconnected tools."
            ),
            "interpretation": "A recurring terminology retrieval problem may exist.",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "candidate"
    assert body["source_uri"] == "notes://field-interview/2026-08-02-translator"
    assert body["original_material"].startswith("I keep approved terminology")
    assert body["observation"].startswith("The translator described")
    assert body["interpretation"].startswith("A recurring")
    assert body["captured_at"]


async def test_evidence_inbox_lists_candidate_and_signal_traces_back_to_original_material(client):
    created = await client.post(
        "/api/external-signals",
        json={
            "source_label": "Support call",
            "original_material": "I cannot tell which client requested which revision.",
            "observed_at": "2026-08-02T10:00:00Z",
            "observation": "The caller described losing revision provenance.",
        },
    )
    signal_id = created.json()["id"]

    inbox = await client.get("/api/evidence-inbox")
    detail = await client.get(f"/api/external-signals/{signal_id}")

    assert inbox.status_code == 200
    assert [item["id"] for item in inbox.json()["items"]] == [signal_id]
    assert detail.status_code == 200
    assert detail.json()["original_material"] == (
        "I cannot tell which client requested which revision."
    )


async def test_triage_keeps_audit_trail_when_candidate_is_accepted_ignored_or_flagged(client):
    created = await client.post(
        "/api/external-signals",
        json={
            "source_label": "Field note",
            "original_material": "The team manually reconciles shipment updates each morning.",
            "observed_at": "2026-08-02T11:00:00Z",
            "observation": "A manual reconciliation workflow was reported.",
        },
    )
    signal_id = created.json()["id"]

    ignored = await client.post(
        f"/api/external-signals/{signal_id}/triage",
        json={"status": "ignored", "reason": "This was a one-off operational mistake."},
    )
    flagged = await client.post(
        f"/api/external-signals/{signal_id}/triage",
        json={"status": "flagged", "reason": "Need a second independent observation."},
    )
    accepted = await client.post(
        f"/api/external-signals/{signal_id}/triage",
        json={"status": "accepted", "reason": "Second observation confirmed the workflow."},
    )
    detail = await client.get(f"/api/external-signals/{signal_id}")

    assert ignored.status_code == 200
    assert flagged.status_code == 200
    assert accepted.status_code == 200
    assert detail.json()["status"] == "accepted"
    assert [event["status"] for event in detail.json()["triage_events"]] == [
        "ignored",
        "flagged",
        "accepted",
    ]
    assert detail.json()["triage_events"][0]["reason"] == "This was a one-off operational mistake."
