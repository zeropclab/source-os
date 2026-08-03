"""Tests for the reality-first Today workspace."""


async def test_today_prioritizes_a_running_validation_over_stale_need_action(client):
    need = await client.post(
        "/api/need-issues",
        json={
            "title": "Operators lose time to workflow incidents",
            "target_actor": "production automation operators",
            "context": "after a production workflow failure",
            "problem": "recovery depends on uncertain support and manual retries",
            "desired_outcome": "learn whether a bounded diagnostic is worth validating",
            "next_validation_action": "audit another public incident report",
        },
    )
    experiment = await client.post(
        f"/api/need-issues/{need.json()['id']}/experiments",
        json={
            "hypothesis": "One operator will respond to a bounded research request.",
            "audience": "production automation operators",
            "method": "Send one approved research request and record the result.",
            "budget_cents": 0,
            "time_limit_hours": 24,
            "success_threshold": "One substantive response.",
            "negative_threshold": "No response by the deadline.",
            "stop_condition": "Do not send a follow-up after the deadline.",
            "requires_external_action": True,
        },
    )
    experiment_id = experiment.json()["id"]
    approved = await client.post(
        f"/api/experiments/{experiment_id}/approve",
        json={"operator_note": "One bounded request is approved."},
    )
    assert approved.status_code == 200
    started = await client.post(f"/api/experiments/{experiment_id}/start")
    assert started.status_code == 200

    today = await client.get("/api/today")

    assert today.status_code == 200
    body = today.json()
    assert body["active_validation"]["id"] == experiment_id
    assert body["active_validation"]["status"] == "running"
    assert body["active_validation"]["stop_condition"] == (
        "Do not send a follow-up after the deadline."
    )
    assert "running validation" in body["next_reality_action"]
    assert body["next_reality_action"] != "audit another public incident report"
