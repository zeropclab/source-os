"""PROTOTYPE ONLY — pure Discovery Objective state transitions.

Question: can a Discovery Agent revise a plan from evidence without crossing its
approved boundary, and stop with a useful blocked result instead of looping?
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def initial_state() -> dict[str, Any]:
    return {
        "objective": "检验跨境对账是否是可付费问题，而非泛泛抱怨",
        "objective_status": "active",
        "boundary": {
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
        "assessments": [],
        "pending_approval": None,
        "latest_result": "No assessment yet.",
    }


def transition(state: dict[str, Any], action: str) -> dict[str, Any]:
    """Return a new state after one simulated observation or operator decision."""
    next_state = deepcopy(state)
    boundary = next_state["boundary"]
    plan = next_state["plan"]

    if action == "repetition":
        boundary["request_used"] += 1
        next_state["assessments"].append(
            "同源重复过高：Reddit 新材料没有增加独立信息。"
        )
        plan["version"] += 1
        plan["sources"] = ["Google Play"]
        plan["focus"] = "寻找独立来源中的付费、流失或替代行为"
        next_state["latest_result"] = "Plan revised inside boundary: Reddit → Google Play."
    elif action == "missing_context":
        boundary["request_used"] += 1
        next_state["assessments"].append("候选内容缺少上下文：先补全文和回复链。")
        plan["version"] += 1
        plan["focus"] = "上下文修复：补齐原文、回复链与发生时间"
        next_state["latest_result"] = "Plan revised inside boundary: context repair."
    elif action == "unapproved_source":
        next_state["pending_approval"] = {
            "kind": "source_addition",
            "source": "YouTube",
            "reason": "现有批准来源未覆盖视频评论场景",
        }
        next_state["latest_result"] = "Blocked: new source needs Operator Approval."
    elif action == "approve_source":
        request = next_state["pending_approval"]
        if request and request["kind"] == "source_addition":
            boundary["approved_sources"].append(request["source"])
            plan["version"] += 1
            plan["sources"] = [request["source"]]
            next_state["pending_approval"] = None
            next_state["latest_result"] = "Operator approved boundary change; a new plan is allowed."
        else:
            next_state["latest_result"] = "No source approval is pending."
    elif action == "exhaust_budget":
        boundary["request_used"] = boundary["request_limit"]
        next_state["objective_status"] = "blocked"
        next_state["assessments"].append("请求上限耗尽，尚无足够独立行为证据。")
        next_state["latest_result"] = "Blocked Assessment: request budget exhausted; do not continue."
    elif action == "decide_need":
        next_state["latest_result"] = (
            "Need Hypothesis drafted for operator review; no Need Issue was created automatically."
        )
    else:
        next_state["latest_result"] = "Unknown action."
    return next_state
