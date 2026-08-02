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
    assert "function triageSignal" in page
    assert "Accept as evidence" in page
    assert "Ignore" in page
    assert "Flag for review" in page
    assert "/api/external-signals/${signalId}/triage" in page
    assert '["succeeded", "completed"].includes(run.terminal_state)' in page
    assert "context.missing || []" in page


async def test_source_creation_page_can_define_a_github_issue_source(client):
    response = await client.get("/sources/create")

    assert response.status_code == 200
    page = response.text
    assert '<option value="github">GitHub Issues</option>' in page
    assert "github:'issues'" in page
    assert "github_rest" in page


async def test_need_definition_page_requires_an_explicit_accepted_signal_handoff(client):
    response = await client.get("/needs/create?signal=11111111-1111-1111-1111-111111111111")

    assert response.status_code == 200
    page = response.text
    assert 'id="need-from-signal-form"' in page
    assert 'id="accepted-signal-context"' in page
    assert "/api/external-signals/${signalId}" in page
    assert "/api/need-issues/from-accepted-signal" in page
    assert "This creates a captured Need Issue, not a validated demand" in page
