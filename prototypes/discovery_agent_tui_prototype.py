"""PROTOTYPE ONLY — run with: uv run python prototypes/discovery_agent_tui_prototype.py."""

from __future__ import annotations

import json

from discovery_agent_state_machine import initial_state, transition


def render(state: dict) -> None:
    print("\033[2J\033[H", end="")
    print("DISCOVERY AGENT STATE-MACHINE PROTOTYPE")
    print("Question: can evidence change plans without crossing approvals?\n")
    print(json.dumps(state, ensure_ascii=False, indent=2))
    print("\n[r] 同源重复  [c] 上下文缺失  [x] 请求新信源  [o] 批准新信源")
    print("[b] 耗尽预算  [n] 草拟 Need Hypothesis  [q] 退出")


def main() -> None:
    state = initial_state()
    command_map = {
        "r": "repetition",
        "c": "missing_context",
        "x": "unapproved_source",
        "o": "approve_source",
        "b": "exhaust_budget",
        "n": "decide_need",
    }
    while True:
        render(state)
        command = input("\n> ").strip().lower()
        if command == "q":
            return
        state = transition(state, command_map.get(command, "unknown"))


if __name__ == "__main__":
    main()
