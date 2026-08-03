"""Public workbench contract for operating an Acquisition Mission."""


async def test_missions_workbench_exposes_an_explicit_bounded_mission_flow(client):
    response = await client.get("/missions")

    assert response.status_code == 200
    page = response.text
    assert 'id="mission-form"' in page
    assert 'id="source-id"' in page
    assert 'id="source-config-form"' in page
    assert 'id="execution-mode"' in page
    assert 'id="preview-item-limit"' in page
    assert 'id="preview-request-limit"' in page
    assert 'id="preview-mission"' in page
    assert 'id="queue-mission"' in page
    assert 'value="fixture"' in page
    assert 'value="live"' in page
    assert 'id="mission-result"' in page
    assert 'id="mission-history"' in page
    assert 'id="refresh-missions"' in page
    assert 'id="evidence-inbox"' in page
    assert "/api/acquisition-missions" in page
    assert "/dry-runs" in page
    assert "/queued-runs" in page
    assert "/execute" in page
    assert "/retry" in page
    assert "Retry as new run" in page
    assert "/api/evidence-inbox" in page
    assert "/api/acquisition-missions/${missionId}/runs" in page
    assert "function openHistoricalMission" in page
    assert "function openHistoricalRun" in page
    assert "function triageSignal" in page
    assert "Accept as evidence" in page
    assert "Ignore" in page
    assert "Flag for review" in page
    assert "/api/external-signals/${signalId}/triage" in page
    assert '["succeeded", "completed"].includes(run.terminal_state)' in page
    assert "context.missing || []" in page
    assert "Preview only" in page
    assert "Worker attempts" in page
    assert "Lease" in page


async def test_dashboard_prioritizes_collection_workbench_over_validation_tasks(client):
    response = await client.get("/")

    assert response.status_code == 200
    page = response.text
    assert 'id="collection-workbench"' in page
    assert "Open collection workbench" in page
    assert "Define a source" in page
    assert "Review collected evidence" in page
    assert "/missions" in page
    assert "/sources/create" in page
    assert "/api/evidence-inbox" in page
    assert "/api/today" not in page
    assert "Strongest objection" not in page
    assert "Next reality action" not in page
    assert "Success Rate (24h)" not in page
    assert "Items Collected" not in page


async def test_manual_observation_workbench_imports_traceable_reality_signals(client):
    response = await client.get("/observations")

    assert response.status_code == 200
    page = response.text
    assert 'id="manual-observation-form"' in page
    assert 'id="observation-original-material"' in page
    assert 'id="observation-observed-at"' in page
    assert "/api/external-signals" in page
    assert "does not validate a Need" in page


async def test_source_creation_page_can_define_a_github_issue_source(client):
    response = await client.get("/sources/create")

    assert response.status_code == 200
    page = response.text
    assert '<option value="github">GitHub Issues</option>' in page
    assert "github:'issues'" in page
    assert "github_rest" in page


async def test_source_detail_exposes_immutable_configuration_history(client):
    response = await client.get("/sources/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 200
    page = response.text
    assert 'id="source-config-history"' in page
    assert "/api/sources/11111111-1111-1111-1111-111111111111/config-versions" in page
    assert "Configuration History" in page
    assert "immutable" in page


async def test_need_definition_page_requires_an_explicit_accepted_signal_handoff(client):
    response = await client.get("/needs/create?signal=11111111-1111-1111-1111-111111111111")

    assert response.status_code == 200
    page = response.text
    assert 'id="need-from-signal-form"' in page
    assert 'id="accepted-signal-context"' in page
    assert "/api/external-signals/${signalId}" in page
    assert "/api/need-issues/from-accepted-signal" in page
    assert "This creates a captured Need Issue, not a validated demand" in page


async def test_need_library_lists_persisted_problem_hypotheses_without_claiming_validation(client):
    response = await client.get("/needs")

    assert response.status_code == 200
    page = response.text
    assert 'id="need-library"' in page
    assert 'id="need-status-filter"' in page
    assert "/api/need-issues?page=1&page_size=100" in page
    assert "Evidence counts describe stored references only" in page
    assert "Open validation workbench" in page


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

    experiment_page = await client.get("/needs/experiments/11111111-1111-1111-1111-111111111111")
    assert experiment_page.status_code == 200
    assert 'id="execution-task-form"' in experiment_page.text
    assert 'id="execution-task-list"' in experiment_page.text
    assert "/execution-tasks" in experiment_page.text
    assert "mark-contacted" in experiment_page.text

    library = await client.get("/experiments")
    assert library.status_code == 200
    library_page = library.text
    assert 'id="experiment-library"' in library_page
    assert 'id="experiment-status-filter"' in library_page
    assert "/api/experiments?page=1&page_size=100" in library_page
    assert "Open experiment workbench" in library_page


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

    library = await client.get("/features")
    assert library.status_code == 200
    library_page = library.text
    assert 'id="feature-library"' in library_page
    assert 'id="feature-status-filter"' in library_page
    assert "/api/features?page=1&page_size=100" in library_page
    assert "Open delivery workbench" in library_page


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

    library = await client.get("/product-theses")
    assert library.status_code == 200
    library_page = library.text
    assert 'id="thesis-library"' in library_page
    assert 'id="thesis-status-filter"' in library_page
    assert "/api/product-theses?page=1&page_size=100" in library_page
    assert "Open decision workbench" in library_page


async def test_delivery_workbench_exposes_review_release_tracking_and_outcome_controls(client):
    response = await client.get("/features/11111111-1111-1111-1111-111111111111/delivery")

    assert response.status_code == 200
    page = response.text
    assert 'id="delivery-workbench"' in page
    assert 'id="delivery-record-form"' in page
    assert 'id="release-delivery-form"' in page
    assert 'id="feature-outcome-form"' in page
    assert 'id="outcome-decision-form"' in page
    assert "/api/delivery-records/features/${featureId}/workbench" in page
    assert "not proof of product success" in page


async def test_pi_agent_workbench_exposes_bounded_evidence_and_operator_review_controls(client):
    response = await client.get("/agents")

    assert response.status_code == 200
    page = response.text
    assert 'id="agent-run-form"' in page
    assert 'id="agent-signal-ids"' in page
    assert 'id="agent-max-tokens"' in page
    assert "/api/agent-runs" in page
    assert "cannot collect" in page

    detail = await client.get("/agents/11111111-1111-1111-1111-111111111111")
    assert detail.status_code == 200
    detail_page = detail.text
    assert 'id="agent-run-detail"' in detail_page
    assert 'id="agent-execute-form"' in detail_page
    assert 'id="agent-cancel-form"' in detail_page
    assert 'id="agent-decision-form"' in detail_page
    assert "/api/agent-runs/${runId}" in detail_page


async def test_ontology_workbench_exposes_falsifiable_hypothesis_controls(client):
    response = await client.get("/ontology")

    assert response.status_code == 200
    page = response.text
    assert 'id="ontology-hypothesis-form"' in page
    assert 'id="relationship-path"' in page
    assert 'id="counterexample"' in page
    assert 'id="smallest-validation-action"' in page
    assert "/api/ontology-hypotheses" in page
    assert "not a validated Need" in page


async def test_source_portfolio_workbench_exposes_decision_value_and_bias_controls(client):
    response = await client.get("/portfolio")

    assert response.status_code == 200
    page = response.text
    assert 'id="source-portfolio-form"' in page
    assert 'id="portfolio-source-id"' in page
    assert 'id="portfolio-counterevidence-count"' in page
    assert 'id="portfolio-decision-impact"' in page
    assert "/api/source-portfolio/assessments" in page
    assert "does not prove coverage" in page
