"""Fixture-only acceptance journey across SourceOS product mechanisms."""

from apps.api.dependencies import get_github_mission_transport
from apps.api.main import app
from packages.adapters.github_mission import GitHubFixtureTransport
from tests.api.test_acquisition_mission_runs import _create_github_mission


async def test_fixture_assets_can_flow_from_bounded_collection_to_outcome_decision(client):
    """Synthetic records prove workflow mechanics, never real demand or profitability."""
    mission, _ = await _create_github_mission(client)
    app.dependency_overrides[get_github_mission_transport] = lambda: GitHubFixtureTransport(
        scenario="issue_with_context"
    )
    run = await client.post(
        f"/api/acquisition-missions/{mission['id']}/runs", json={"execution_mode": "fixture"}
    )
    assert run.status_code == 201
    assert run.json()["execution_mode"] == "fixture"
    signal_ids = run.json()["external_signal_ids"]

    accepted = await client.post(
        f"/api/external-signals/{signal_ids[0]}/triage",
        json={"status": "accepted", "reason": "Synthetic fixture signal is traceable."},
    )
    assert accepted.status_code == 200
    need = await client.post(
        "/api/need-issues/from-accepted-signal",
        json={
            "external_signal_id": signal_ids[0],
            "title": "Fixture operators reconcile payout records manually",
            "target_actor": "fixture operator",
            "context": "during payout reconciliation",
            "problem": "records require a repeated manual comparison",
            "desired_outcome": "identify mismatches without repeated manual work",
            "unknowns": ["Whether independent operators would pay for a solution"],
            "next_validation_action": "obtain an independent real-world observation",
        },
    )
    assert need.status_code == 201
    need_id = need.json()["id"]
    counter = await client.post(
        f"/api/need-issues/{need_id}/evidence",
        json={
            "reference_type": "fixture_counterexample",
            "reference_uri": "fixture://counterexample/1",
            "external_signal_id": signal_ids[1],
            "role": "counter",
            "excerpt": "Synthetic counterexample: existing automation may solve the workflow.",
        },
    )
    challenge = await client.post(
        f"/api/need-issues/{need_id}/challenges",
        json={
            "basis": "A fixture cannot establish an independent recurring problem.",
            "unknowns": ["Whether a real operator experiences the task"],
            "falsification_condition": "A real operator uses existing automation without pain.",
            "smallest_next_action": "Record one real counterexample or supporting observation.",
            "assessment": "insufficient-evidence",
        },
    )
    assert counter.status_code == 201
    assert challenge.status_code == 201
    validated = await client.post(
        f"/api/need-issues/{need_id}/transition",
        json={
            "status": "discovery-validated",
            "override_gate": True,
            "reason": "FIXTURE ONLY: validates state-machine wiring, not a market conclusion.",
        },
    )
    assert validated.status_code == 200

    agent = await client.post(
        "/api/agent-runs",
        json={
            "evidence_signal_ids": signal_ids,
            "task_instruction": "Propose a falsifiable hypothesis; do not validate it.",
            "idempotency_key": "fixture-lifecycle-agent-v1",
            "model_version": "pi-faux-v1",
            "prompt_version": "fixture-acceptance-v1",
            "max_tool_calls": 1,
            "max_tokens": 500,
            "max_cost_cents": 0,
        },
    )
    assert agent.status_code == 201
    agent_run = await client.post(f"/api/agent-runs/{agent.json()['id']}/execute")
    assert agent_run.status_code == 200
    assert agent_run.json()["output"]["cannot_conclude"]

    experiment = await client.post(
        f"/api/need-issues/{need_id}/experiments",
        json={
            "hypothesis": "A real operator will describe a recurring reconciliation task.",
            "audience": "one independent operator",
            "method": (
                "future real-world observation; fixture currently exercises the mechanism only"
            ),
            "budget_cents": 0,
            "time_limit_hours": 1,
            "success_threshold": "One independently traceable observation",
            "negative_threshold": "A counterexample removes the task",
            "stop_condition": "Stop after one bounded observation",
            "requires_external_action": False,
        },
    )
    assert experiment.status_code == 201
    experiment_id = experiment.json()["id"]
    assert (await client.post(f"/api/experiments/{experiment_id}/start")).status_code == 200
    assert (
        await client.post(
            f"/api/experiments/{experiment_id}/observations",
            json={"kind": "silence", "observation": "FIXTURE ONLY: no market inference."},
        )
    ).status_code == 201
    assert (
        await client.post(
            f"/api/experiments/{experiment_id}/decision",
            json={"decision": "change", "rationale": "Fixture outcome is not a market result."},
        )
    ).status_code == 200

    thesis = await client.post(
        f"/api/need-issues/{need_id}/product-theses",
        json={
            "title": "Fixture reconciliation concierge",
            "user": "fixture operator",
            "beneficiary": "fixture operator",
            "decision_maker": "fixture operator",
            "payer": "fixture operator",
            "trigger": "a payout record is mismatched",
            "promised_outcome": "surface one mismatch quickly",
            "alternative": "manual comparison",
            "channel": "future direct outreach",
            "price_cents": 100,
            "delivery_mechanism": "manual concierge",
            "delivery_mode": "manual",
        },
    )
    assert thesis.status_code == 201
    thesis_id = thesis.json()["id"]
    assert (
        await client.post(
            f"/api/product-theses/{thesis_id}/observations",
            json={
                "kind": "quote",
                "observation": "FIXTURE ONLY: offer record.",
                "amount_cents": 100,
            },
        )
    ).status_code == 201
    assert (
        await client.post(
            f"/api/product-theses/{thesis_id}/decision",
            json={"decision": "continue", "rationale": "Fixture gate exercise only."},
        )
    ).status_code == 200
    assert (
        await client.post(
            f"/api/product-theses/{thesis_id}/build-authorization",
            json={"rationale": "Fixture authorization for a bounded implementation contract."},
        )
    ).status_code == 201

    feature = await client.post(
        f"/api/need-issues/{need_id}/features",
        json={
            "product_thesis_id": thesis_id,
            "title": "Fixture mismatch list",
            "user_task": "Review one mismatched payout record",
            "scope": "one manual mismatch list",
            "explicit_exclusions": ["No automatic payment action"],
            "acceptance_criteria": ["Shows one fixture mismatch"],
            "tracking_events": ["fixture_mismatch_viewed"],
            "tracking_properties": ["fixture_run_id"],
            "success_metric": "A future real operator completes the task",
            "negative_metric": "A future real operator abandons the task",
            "rollback_condition": "Disable the list if it blocks reconciliation",
        },
    )
    assert feature.status_code == 201
    feature_id = feature.json()["id"]
    delivery = await client.post(
        f"/api/delivery-records/features/{feature_id}/deliveries",
        json={
            "branch": "test/fixture-lifecycle-acceptance",
            "implementation_version": "fixture-v0.1",
            "tests_evidence": "fixture lifecycle acceptance passed",
            "review_conclusion": "fixture review complete",
            "risk": "no real users or market data",
            "migration_evidence": "no migration",
            "rollback_evidence": "disable fixture route",
            "acceptance_evidence": "fixture path completed",
            "tracking_evidence": "fixture_mismatch_viewed declared",
            "pr_reference": "local-git://fixture-lifecycle",
        },
    )
    assert delivery.status_code == 201
    delivery_id = delivery.json()["id"]
    assert (await client.post(f"/api/delivery-records/{delivery_id}/release")).status_code == 200
    assert (
        await client.post(
            f"/api/feature-outcomes/deliveries/{delivery_id}/outcomes",
            json={
                "kind": "cost",
                "observation": "FIXTURE ONLY: synthetic processing cost.",
                "amount_cents": 0,
            },
        )
    ).status_code == 201
    outcome_decision = await client.post(
        f"/api/feature-outcomes/deliveries/{delivery_id}/decision",
        json={
            "decision": "iterate",
            "threshold_comparison": "Fixture data does not satisfy any market threshold.",
            "contribution_margin_cents": 0,
            "rationale": "Do not infer retention, payment, or profitability from fixture records.",
        },
    )
    assert outcome_decision.status_code == 200
    assert outcome_decision.json()["decision"] == "iterate"
