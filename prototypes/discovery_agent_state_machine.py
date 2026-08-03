"""PROTOTYPE ONLY — pure Discovery Objective state transitions.

Question: can a Discovery Agent revise a plan from evidence without crossing its
approved boundary, and can it be made unable to act after stopping?
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def initial_state() -> dict[str, Any]:
    return {
        "objective": "检验跨境对账是否是可付费问题，而非泛泛抱怨",
        "objective_status": "active",
        "boundary": {
            "version": 1,
            "approved_sources": ["Reddit", "Google Play"],
            "request_limit": 12,
            "request_used": 0,
            "cost_limit_cents": 0,
            "cost_used_cents": 0,
        },
        "plan": {
            "version": 1,
            "focus": "寻找已付出时间或金钱的行为证据",
            "sources": ["Reddit"],
            "counterevidence_target": "已有工具是否已解决问题",
        },
        "evidence": [],
        "assessments": [],
        "pending_approval": None,
        "latest_result": "No assessment yet.",
    }


def _next_id(prefix: str, values: list[dict]) -> str:
    return f"{prefix}-{len(values) + 1:03d}"


def _append_assessment(state: dict[str, Any], kind: str, statement: str, evidence_ids: list[str]) -> None:
    state["assessments"].append(
        {
            "id": _next_id("ASMT", state["assessments"]),
            "kind": kind,
            "statement": statement,
            "evidence_ids": evidence_ids,
        }
    )


def _consume_request(state: dict[str, Any]) -> bool:
    boundary = state["boundary"]
    if boundary["request_used"] >= boundary["request_limit"]:
        state["objective_status"] = "blocked"
        _append_assessment(state, "blocked", "请求上限耗尽，尚无足够独立行为证据。", [])
        state["latest_result"] = "Blocked Assessment: request budget exhausted; do not continue."
        return False
    boundary["request_used"] += 1
    return True


def transition(state: dict[str, Any], action: str) -> dict[str, Any]:
    """Return a new state after one simulated observation or operator decision."""
    next_state = deepcopy(state)
    boundary = next_state["boundary"]
    plan = next_state["plan"]
    status = next_state["objective_status"]

    if status in {"blocked", "completed"} and action != "boundary_revision":
        next_state["latest_result"] = "Rejected: a stopped Objective only permits Operator Boundary Revision."
        return next_state
    if status == "pending_approval" and action not in {"approve_source", "reject_source"}:
        next_state["latest_result"] = "Rejected: resolve the pending Operator Approval first."
        return next_state

    if action == "repetition":
        if not _consume_request(next_state):
            return next_state
        _append_assessment(next_state, "counterevidence", "同源重复过高：Reddit 新材料没有增加独立信息。", [])
        plan["version"] += 1
        plan["sources"] = ["Google Play"]
        plan["focus"] = "寻找独立来源中的付费、流失或替代行为"
        next_state["latest_result"] = "Plan revised inside boundary: Reddit → Google Play."
    elif action == "missing_context":
        if not _consume_request(next_state):
            return next_state
        _append_assessment(next_state, "coverage_gap", "候选内容缺少上下文：先补全文和回复链。", [])
        plan["version"] += 1
        plan["focus"] = "上下文修复：补齐原文、回复链与发生时间"
        next_state["latest_result"] = "Plan revised inside boundary: context repair."
    elif action == "unapproved_source":
        next_state["pending_approval"] = {
            "kind": "source_addition",
            "source": "YouTube",
            "reason": "现有批准来源未覆盖视频评论场景",
        }
        next_state["objective_status"] = "pending_approval"
        next_state["latest_result"] = "Blocked: new source needs Operator Approval."
    elif action == "approve_source":
        request = next_state["pending_approval"]
        if request and request["kind"] == "source_addition":
            boundary["approved_sources"].append(request["source"])
            plan["version"] += 1
            plan["sources"] = [request["source"]]
            next_state["pending_approval"] = None
            next_state["objective_status"] = "active"
            next_state["latest_result"] = "Operator approved boundary change; a new plan is allowed."
        else:
            next_state["latest_result"] = "No source approval is pending."
    elif action == "reject_source":
        next_state["pending_approval"] = None
        next_state["objective_status"] = "active"
        next_state["latest_result"] = "Operator rejected boundary change; continue only with approved sources."
    elif action == "record_behavior_evidence":
        if not _consume_request(next_state):
            return next_state
        evidence_id = _next_id("EVID", next_state["evidence"])
        next_state["evidence"].append(
            {
                "id": evidence_id,
                "kind": "behavior",
                "source": plan["sources"][0],
                "statement": "操作者付出时间或金钱来规避跨境对账错误。",
            }
        )
        _append_assessment(
            next_state,
            "support",
            "存在可追溯的行为成本，但付费意愿仍未知。",
            [evidence_id],
        )
        next_state["latest_result"] = "Support Assessment recorded with traceable evidence."
    elif action == "exhaust_budget":
        boundary["request_used"] = boundary["request_limit"]
        _consume_request(next_state)
    elif action == "decide_need":
        supporting = [item for item in next_state["assessments"] if item["kind"] == "support"]
        if not supporting:
            next_state["latest_result"] = "Rejected: Need Hypothesis needs a support Assessment with evidence."
        else:
            next_state["latest_result"] = (
                "Need Hypothesis drafted from a cited Assessment; no Need Issue was created automatically."
            )
    elif action == "boundary_revision":
        if status != "blocked":
            next_state["latest_result"] = "Rejected: only a blocked Objective can receive a Boundary Revision."
        else:
            boundary["version"] += 1
            boundary["request_limit"] += 12
            next_state["objective_status"] = "active"
            plan["version"] += 1
            next_state["latest_result"] = "Operator Boundary Revision extended request budget; new plan is active."
    else:
        next_state["latest_result"] = "Unknown action."
    return next_state
