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


async def test_need_validation_workbench_exposes_counterevidence_challenge_and_experiment_forms(
    client,
):
    response = await client.get("/needs/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 200
    page = response.text
    assert 'id="need-detail"' in page
    assert 'id="need-evidence-form"' in page
    assert 'id="need-challenge-form"' in page
    assert 'id="validation-experiment-form"' in page
    assert "/api/need-issues/${needId}" in page
    assert "/evidence" in page
    assert "/challenges" in page
    assert "/experiments" in page
    assert "No action here marks this Need Issue as discovery-validated" in page


async def test_feature_definition_page_exposes_tracking_and_rollback_contract(client):
    response = await client.get("/features/create?need=11111111-1111-1111-1111-111111111111")

    assert response.status_code == 200
    page = response.text
    assert 'id="feature-definition-form"' in page
    assert 'id="product-thesis-id"' in page
    assert 'id="tracking-events"' in page
    assert 'id="rollback-condition"' in page
    assert '/api/need-issues/${value("need-id")}/features' in page
    assert "build authorization" in page


async def test_product_thesis_workbench_exposes_decision_controls(client):
    response = await client.get("/product-theses/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 200
    page = response.text
    assert 'id="product-thesis-detail"' in page
    assert 'id="thesis-observation-form"' in page
    assert 'id="thesis-decision-form"' in page
    assert 'id="build-authorization-form"' in page
    assert "/api/product-theses/${thesisId}/workbench" in page
    assert "/build-authorization" in page
    assert "not market proof" in page
