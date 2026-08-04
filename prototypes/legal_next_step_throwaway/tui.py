"""PROTOTYPE ONLY — interactive shell for the Legal Next Step engine."""

import os
from dataclasses import replace

from .engine import Facts, evaluate_nested, evaluate_table, facts_dict

BOLD = "\x1b[1m"
DIM = "\x1b[2m"
RESET = "\x1b[0m"

LIFECYCLES = ("active", "pending_approval", "blocked", "completed")
WORK_STATUSES = ("none", "queued", "running", "failed")


def cycle(current: str, choices: tuple[str, ...]) -> str:
    return choices[(choices.index(current) + 1) % len(choices)]


def render(facts: Facts) -> None:
    os.system("clear" if os.name != "nt" else "cls")
    decision = evaluate_table(facts)
    nested = evaluate_nested(facts)
    print(f"{BOLD}PROTOTYPE — Legal Next Step engine{RESET}")
    print(f"{DIM}Everything below is derived from an in-memory fact snapshot.{RESET}\n")
    print(f"{BOLD}Current facts{RESET}")
    for key, value in facts_dict(facts).items():
        print(f"  {key:24} {value}")
    print(f"\n{BOLD}Decision-table result{RESET}")
    print(f"  matched rule             {decision.rule}")
    print(f"  operational state        {decision.operational_state}")
    print(f"  Legal Next Step          {decision.legal_next_step}")
    print(f"  why                      {decision.explanation}")
    print(f"\n{BOLD}Rule trace{RESET}")
    for entry in decision.trace:
        print(f"  {entry}")
    print(f"\n{BOLD}Nested-conditional comparison{RESET}")
    print(f"  result                    {nested[0]} / {nested[1]}")
    print(f"  agrees with table         {nested == (decision.operational_state, decision.legal_next_step)}")
    print(f"\n{BOLD}Actions{RESET}")
    print("  [l] lifecycle   [b] boundary current   [a] acquisition work")
    print("  [g] agent work  [e] add evidence       [t] triage evidence")
    print("  [p] add proposal [v] review proposal   [s] stop condition")
    print("  [n] current plan [m] ready Mission     [r] reset   [q] quit")


def apply_action(facts: Facts, action: str) -> Facts:
    if action == "l":
        return replace(facts, lifecycle=cycle(facts.lifecycle, LIFECYCLES))
    if action == "b":
        return replace(facts, boundary_current=not facts.boundary_current)
    if action == "a":
        return replace(
            facts, acquisition_work=cycle(facts.acquisition_work, WORK_STATUSES)
        )
    if action == "g":
        return replace(facts, agent_work=cycle(facts.agent_work, WORK_STATUSES))
    if action == "e":
        return replace(facts, untriaged_evidence=facts.untriaged_evidence + 1)
    if action == "t":
        return replace(facts, untriaged_evidence=0)
    if action == "p":
        return replace(facts, unreviewed_proposals=facts.unreviewed_proposals + 1)
    if action == "v":
        return replace(facts, unreviewed_proposals=0)
    if action == "s":
        return replace(facts, stop_condition_met=not facts.stop_condition_met)
    if action == "n":
        return replace(facts, has_current_plan=not facts.has_current_plan)
    if action == "m":
        return replace(facts, plan_has_ready_mission=not facts.plan_has_ready_mission)
    if action == "r":
        return Facts()
    return facts


def main() -> None:
    facts = Facts()
    while True:
        render(facts)
        action = input("\nAction: ").strip().lower()[:1]
        if action == "q":
            break
        facts = apply_action(facts, action)


if __name__ == "__main__":
    main()
