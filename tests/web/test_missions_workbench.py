"""Public workbench contract for operating an Acquisition Mission."""


async def test_missions_workbench_exposes_an_explicit_bounded_mission_flow(client):
    response = await client.get("/missions")

    assert response.status_code == 200
    page = response.text
    assert 'id="mission-form"' in page
    assert 'id="source-id"' in page
    assert 'id="source-config-form"' in page
    assert 'id="execution-mode"' in page
    assert 'value="fixture"' in page
    assert 'value="live"' in page
    assert 'id="mission-result"' in page
    assert 'id="evidence-inbox"' in page
    assert "/api/acquisition-missions" in page
    assert "/api/evidence-inbox" in page
    assert '["succeeded", "completed"].includes(run.terminal_state)' in page
