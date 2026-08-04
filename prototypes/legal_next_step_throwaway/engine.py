"""PROTOTYPE ONLY — pure Legal Next Step evaluators."""

from dataclasses import asdict, dataclass
from typing import Callable, Literal

Lifecycle = Literal["active", "pending_approval", "blocked", "completed"]
WorkStatus = Literal["none", "queued", "running", "failed"]


@dataclass(frozen=True)
class Facts:
    lifecycle: Lifecycle = "active"
    boundary_current: bool = True
    acquisition_work: WorkStatus = "none"
    agent_work: WorkStatus = "none"
    untriaged_evidence: int = 0
    unreviewed_proposals: int = 0
    stop_condition_met: bool = False
    has_current_plan: bool = False
    plan_has_ready_mission: bool = False


@dataclass(frozen=True)
class Decision:
    rule: str
    operational_state: str
    legal_next_step: str
    explanation: str
    trace: tuple[str, ...]


Predicate = Callable[[Facts], bool]


@dataclass(frozen=True)
class Rule:
    name: str
    predicate: Predicate
    operational_state: str
    legal_next_step: str
    explanation: str


def _active_work(facts: Facts) -> bool:
    return facts.acquisition_work in {"queued", "running"} or facts.agent_work in {
        "queued",
        "running",
    }


def _failed_work(facts: Facts) -> bool:
    return facts.acquisition_work == "failed" or facts.agent_work == "failed"


RULES = (
    Rule(
        "completed",
        lambda f: f.lifecycle == "completed",
        "completed",
        "review_decision_and_outcomes",
        "A completed Objective is terminal; only its Decision Record and feedback remain actionable.",
    ),
    Rule(
        "blocked",
        lambda f: f.lifecycle == "blocked",
        "blocked",
        "create_boundary_revision",
        "Blocked Objectives regain capacity only through a material Boundary Revision.",
    ),
    Rule(
        "pending-approval",
        lambda f: f.lifecycle == "pending_approval",
        "awaiting_operator_approval",
        "decide_approval_request",
        "Permission expansion must be decided before further Agent or collection work.",
    ),
    Rule(
        "stop-active-work",
        lambda f: f.stop_condition_met and _active_work(f),
        "stopping_active_work",
        "cancel_or_finish_active_work",
        "A stop condition forbids new work; currently active work must reach a safe checkpoint.",
    ),
    Rule(
        "closure-decision",
        lambda f: f.stop_condition_met,
        "closure_decision_required",
        "write_discovery_decision_record",
        "A stop condition requires an Operator decision and never completes an Objective automatically.",
    ),
    Rule(
        "stale-boundary",
        lambda f: not f.boundary_current,
        "boundary_attention_required",
        "request_or_select_current_boundary",
        "Work pinned to a stale Boundary cannot proceed.",
    ),
    Rule(
        "active-work",
        _active_work,
        "work_in_progress",
        "monitor_or_control_active_work",
        "Existing work is monitored before duplicate work is started.",
    ),
    Rule(
        "failed-work",
        _failed_work,
        "work_failure_review",
        "review_failure_and_choose_retry",
        "Failure is a fact that requires review; it is not silently retried or treated as no result.",
    ),
    Rule(
        "evidence-triage",
        lambda f: f.untriaged_evidence > 0,
        "evidence_review_required",
        "triage_evidence_candidates",
        "Untriaged material cannot become accepted support.",
    ),
    Rule(
        "proposal-review",
        lambda f: f.unreviewed_proposals > 0,
        "proposal_review_required",
        "review_agent_proposal",
        "Agent output remains a Proposal until an Operator promotes, rejects, or revises it.",
    ),
    Rule(
        "plan-required",
        lambda f: not f.has_current_plan,
        "plan_required",
        "request_or_create_acquisition_plan",
        "An active Objective needs a current Plan before it can create bounded collection work.",
    ),
    Rule(
        "mission-ready",
        lambda f: f.plan_has_ready_mission,
        "ready_to_collect",
        "start_approved_mission",
        "A Mission already allowed by the current Plan and Boundary may be started.",
    ),
    Rule(
        "plan-needs-work",
        lambda _f: True,
        "plan_needs_revision",
        "request_next_bounded_action",
        "The current Plan has no ready Mission, so the Agent may propose the next bounded action.",
    ),
)


def evaluate_table(facts: Facts) -> Decision:
    trace: list[str] = []
    for rule in RULES:
        matched = rule.predicate(facts)
        trace.append(f"{rule.name}: {'MATCH' if matched else 'skip'}")
        if matched:
            return Decision(
                rule=rule.name,
                operational_state=rule.operational_state,
                legal_next_step=rule.legal_next_step,
                explanation=rule.explanation,
                trace=tuple(trace),
            )
    raise AssertionError("The final decision-table rule must always match")


def evaluate_nested(facts: Facts) -> tuple[str, str]:
    """Equivalent behaviour expressed as nested conditionals for comparison."""
    if facts.lifecycle == "completed":
        return "completed", "review_decision_and_outcomes"
    if facts.lifecycle == "blocked":
        return "blocked", "create_boundary_revision"
    if facts.lifecycle == "pending_approval":
        return "awaiting_operator_approval", "decide_approval_request"
    if facts.stop_condition_met:
        if _active_work(facts):
            return "stopping_active_work", "cancel_or_finish_active_work"
        return "closure_decision_required", "write_discovery_decision_record"
    if not facts.boundary_current:
        return "boundary_attention_required", "request_or_select_current_boundary"
    if _active_work(facts):
        return "work_in_progress", "monitor_or_control_active_work"
    if _failed_work(facts):
        return "work_failure_review", "review_failure_and_choose_retry"
    if facts.untriaged_evidence:
        return "evidence_review_required", "triage_evidence_candidates"
    if facts.unreviewed_proposals:
        return "proposal_review_required", "review_agent_proposal"
    if not facts.has_current_plan:
        return "plan_required", "request_or_create_acquisition_plan"
    if facts.plan_has_ready_mission:
        return "ready_to_collect", "start_approved_mission"
    return "plan_needs_revision", "request_next_bounded_action"


def facts_dict(facts: Facts) -> dict:
    return asdict(facts)
