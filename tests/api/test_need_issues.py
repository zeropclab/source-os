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

    thesis = await client.post(
        f"/api/need-issues/{need_id}/product-theses",
        json={
            "title": "Clinic follow-up concierge pilot",
            "user": "clinic coordinator",
            "beneficiary": "clinic coordinator",
            "decision_maker": "clinic owner",
            "payer": "clinic owner",
            "trigger": "an appointment remains unconfirmed",
            "promised_outcome": "identify follow-up work quickly",
            "alternative": "manual calls and messages",
            "channel": "direct pilot outreach",
            "price_cents": 1000,
            "delivery_mechanism": "manual status-board setup",
            "delivery_mode": "manual",
        },
    )
    thesis_id = thesis.json()["id"]
    blocked_feature = await client.post(
        f"/api/need-issues/{need_id}/features",
        json={
            "product_thesis_id": thesis_id,
            "title": "Premature feature",
            "user_task": "Do one bounded task",
            "scope": "One narrow workflow",
            "explicit_exclusions": ["No automation"],
            "acceptance_criteria": ["Completes the bounded task"],
            "tracking_events": ["feature_viewed"],
            "tracking_properties": ["thesis_id"],
            "success_metric": "One completed task",
            "negative_metric": "No completed tasks",
            "rollback_condition": "Remove the feature if it blocks the task.",
        },
    )
    assert blocked_feature.status_code == 409
    assert "build authorization" in blocked_feature.json()["detail"]
    await client.post(
        f"/api/product-theses/{thesis_id}/observations",
        json={"kind": "quote", "observation": "A pilot quote was prepared.", "amount_cents": 1000},
    )
    await client.post(
        f"/api/product-theses/{thesis_id}/decision",
        json={"decision": "continue", "rationale": "Proceed to a bounded build decision."},
    )
    authorization = await client.post(
        f"/api/product-theses/{thesis_id}/build-authorization",
        json={"rationale": "The bounded manual test warrants a build definition."},
    )
    assert authorization.status_code == 201

    feature = await client.post(
        f"/api/need-issues/{need_id}/features",
        json={
            "product_thesis_id": thesis_id,
            "title": "Confirmation follow-up board",
            "user_task": "Review tomorrow's appointments and send one follow-up",
            "scope": "Manual import and a status board only",
            "explicit_exclusions": ["No automated messaging in the pilot"],
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
            "rollback_condition": "Roll back if coordinators cannot identify a follow-up task.",
        },
    )

    assert feature.status_code == 201
    body = feature.json()
    assert body["need_issue_id"] == need_id
    assert body["status"] == "defined"

    delivery = await client.post(
        f"/api/delivery-records/features/{body['id']}/deliveries",
        json={"branch": "feat/confirmation-board", "implementation_version": "v0.1.0"},
    )
    assert delivery.status_code == 201
    blocked_release = await client.post(f"/api/delivery-records/{delivery.json()['id']}/release")
    assert blocked_release.status_code == 409
    assert "acceptance_evidence" in blocked_release.json()["detail"]

    releasable = await client.post(
        f"/api/delivery-records/features/{body['id']}/deliveries",
        json={
            "branch": "feat/confirmation-board",
            "implementation_version": "v0.1.1",
            "tests_evidence": "pytest tests/api/test_need_issues.py -q passed",
            "review_conclusion": "Reviewed: bounded scope is accepted.",
            "risk": "Manual import is the only supported input.",
            "migration_evidence": "No schema migration required.",
            "rollback_evidence": "Disable the board route and retain imported data.",
            "acceptance_evidence": "Coordinator completed the defined acceptance path.",
            "tracking_evidence": "follow_up_board_viewed is configured.",
            "pr_reference": "local-git://feat/confirmation-board",
        },
    )
    released = await client.post(f"/api/delivery-records/{releasable.json()['id']}/release")
    assert released.status_code == 200
    assert released.json()["status"] == "released"


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


async def test_validation_experiment_requires_approval_before_external_work_and_records_reality(
    client,
):
    created = await client.post(
        "/api/need-issues",
        json={
            "title": "Independent translators lose terminology decisions",
            "target_actor": "independent translators with repeat clients",
            "context": "when starting a revision for a repeat client",
            "problem": "approved terminology is scattered across past work",
            "desired_outcome": "reuse client-approved terms without manual searching",
            "unknowns": ["Whether they would pay for a terminology workflow"],
            "next_validation_action": "ask five translators about a paid pilot",
        },
    )
    need_id = created.json()["id"]

    experiment = await client.post(
        f"/api/need-issues/{need_id}/experiments",
        json={
            "hypothesis": (
                "Repeat-client translators will commit to a paid pilot for term memory."
            ),
            "audience": "Independent translators with at least three repeat clients.",
            "method": "Send five individual pilot invitations with a price quote.",
            "budget_cents": 3000,
            "time_limit_hours": 72,
            "success_threshold": "At least two paid-pilot commitments.",
            "negative_threshold": "Zero replies after five invitations.",
            "stop_condition": "Stop after five invitations or 72 hours, whichever comes first.",
            "requires_external_action": True,
        },
    )
    assert experiment.status_code == 201
    experiment_id = experiment.json()["id"]
    assert experiment.json()["status"] == "draft"

    blocked = await client.post(f"/api/experiments/{experiment_id}/start")
    assert blocked.status_code == 409
    assert "operator approval" in blocked.json()["detail"]

    approved = await client.post(
        f"/api/experiments/{experiment_id}/approve",
        json={"operator_note": "I will personally send only these five invitations."},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    started = await client.post(f"/api/experiments/{experiment_id}/start")
    assert started.status_code == 200
    assert started.json()["status"] == "running"

    refusal = await client.post(
        f"/api/experiments/{experiment_id}/observations",
        json={
            "kind": "refusal",
            "observation": "Translator says they already use a spreadsheet and will not pay.",
            "source_uri": "obsidian://validation/translator-1",
        },
    )
    payment = await client.post(
        f"/api/experiments/{experiment_id}/observations",
        json={
            "kind": "payment",
            "observation": "Translator committed to a paid pilot after seeing the price.",
            "amount_cents": 1500,
        },
    )
    assert refusal.status_code == 201
    assert payment.status_code == 201
    assert payment.json()["kind"] == "payment"

    decided = await client.post(
        f"/api/experiments/{experiment_id}/decision",
        json={
            "decision": "change",
            "rationale": (
                "One payment supports willingness to pay, but the refusal narrows the audience."
            ),
        },
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "decided"
    assert decided.json()["decision"] == "change"


async def test_validation_experiment_cannot_close_without_market_observation(client):
    created = await client.post(
        "/api/need-issues",
        json={
            "title": "A concrete claim still needs a market test",
            "target_actor": "a defined operator group",
            "context": "during a repeat workflow",
            "problem": "a manual workaround consumes time",
            "desired_outcome": "test whether a buyer values a replacement",
            "unknowns": ["Whether anyone will commit"],
            "next_validation_action": "run one bounded offer test",
        },
    )
    experiment = await client.post(
        f"/api/need-issues/{created.json()['id']}/experiments",
        json={
            "hypothesis": "A defined buyer will take a concrete next step.",
            "audience": "A defined buyer segment.",
            "method": "Run one bounded offer test.",
            "budget_cents": 0,
            "time_limit_hours": 24,
            "success_threshold": "One concrete next step.",
            "negative_threshold": "No concrete next step.",
            "stop_condition": "Stop after one day.",
            "requires_external_action": False,
        },
    )

    decision = await client.post(
        f"/api/experiments/{experiment.json()['id']}/decision",
        json={"decision": "stop", "rationale": "No conclusion without an observation."},
    )
    assert decision.status_code == 409
    assert "at least one market observation" in decision.json()["detail"]


async def test_product_theses_keep_offer_roles_and_manual_economics_separate(client):
    created = await client.post(
        "/api/need-issues",
        json={
            "title": "A validated workflow can support more than one offer",
            "target_actor": "independent translators",
            "context": "when beginning repeat client work",
            "problem": "approved terminology is scattered",
            "desired_outcome": "reuse client-approved terms",
            "unknowns": ["Which buyer will pay"],
            "next_validation_action": "make a bounded offer",
        },
    )
    need_id = created.json()["id"]
    validated = await client.post(
        f"/api/need-issues/{need_id}/transition",
        json={
            "status": "discovery-validated",
            "override_gate": True,
            "reason": "This test starts from a recorded discovery decision.",
        },
    )
    assert validated.status_code == 200

    manual_offer = {
        "title": "Concierge term-memory pilot",
        "user": "translator preparing a repeat-client revision",
        "beneficiary": "translator and client reviewer",
        "decision_maker": "translator",
        "payer": "translator",
        "trigger": "a repeat client sends a new revision",
        "promised_outcome": "find approved terms within one minute",
        "alternative": "search old documents and chat threads",
        "channel": "individual outreach to repeat-client translators",
        "price_cents": 1500,
        "delivery_mechanism": "manual concierge service using a shared spreadsheet",
        "delivery_mode": "manual",
    }
    thesis = await client.post(f"/api/need-issues/{need_id}/product-theses", json=manual_offer)
    assert thesis.status_code == 201
    thesis_id = thesis.json()["id"]
    assert thesis.json()["delivery_mode"] == "manual"
    assert thesis.json()["payer"] == "translator"

    alternative_offer = await client.post(
        f"/api/need-issues/{need_id}/product-theses",
        json={**manual_offer, "title": "Client terminology review service", "price_cents": 5000},
    )
    assert alternative_offer.status_code == 201
    assert alternative_offer.json()["id"] != thesis_id

    quote = await client.post(
        f"/api/product-theses/{thesis_id}/observations",
        json={
            "kind": "quote",
            "observation": "Quoted a translator a 15 USD concierge pilot.",
            "amount_cents": 1500,
        },
    )
    effort = await client.post(
        f"/api/product-theses/{thesis_id}/observations",
        json={
            "kind": "delivery_effort",
            "observation": "Manual delivery took 45 minutes.",
            "operator_minutes": 45,
        },
    )
    cost = await client.post(
        f"/api/product-theses/{thesis_id}/observations",
        json={
            "kind": "direct_cost",
            "observation": "Translation glossary subscription cost.",
            "amount_cents": 300,
        },
    )
    assert quote.status_code == 201
    assert effort.status_code == 201
    assert cost.status_code == 201

    decided = await client.post(
        f"/api/product-theses/{thesis_id}/decision",
        json={
            "decision": "continue",
            "rationale": "The manual offer is now ready for a real offer test.",
        },
    )
    assert decided.status_code == 200
    assert decided.json()["decision"] == "continue"


async def test_product_thesis_requires_a_discovery_validated_need_and_an_observation_to_decide(
    client,
):
    created = await client.post(
        "/api/need-issues",
        json={
            "title": "An unvalidated problem cannot authorize an offer",
            "target_actor": "a defined actor",
            "context": "a recurring workflow",
            "problem": "a costly manual workaround",
            "desired_outcome": "a measurable replacement",
            "unknowns": ["Whether it repeats"],
            "next_validation_action": "seek a counterexample",
        },
    )
    payload = {
        "title": "A bounded manual offer",
        "user": "operator",
        "beneficiary": "operator",
        "decision_maker": "operator",
        "payer": "operator",
        "trigger": "a repeat task",
        "promised_outcome": "finish the task faster",
        "alternative": "continue manually",
        "channel": "direct contact",
        "price_cents": 1000,
        "delivery_mechanism": "manual service",
        "delivery_mode": "service-assisted",
    }
    blocked = await client.post(
        f"/api/need-issues/{created.json()['id']}/product-theses", json=payload
    )
    assert blocked.status_code == 409
    assert "discovery-validated" in blocked.json()["detail"]
