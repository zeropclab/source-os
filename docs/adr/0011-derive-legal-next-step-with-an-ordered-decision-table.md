---
status: accepted
---

# Derive Legal Next Step with an ordered decision table

The Discovery Orchestrator will derive Workspace Operational State and exactly one Legal Next Step from an immutable current-facts snapshot using a pure, explicitly ordered decision table. Each matched decision exposes a stable rule identifier, operational state, next-step command, human explanation, and evaluation trace; commands must revalidate the relevant Objective and Boundary versions before changing facts.

The priority order begins with terminal completion, blocked Boundary Revision, and pending Operator Approval; then handles stop conditions and safe termination of active work, stale boundaries, active or failed work, Evidence Candidate triage, Agent Proposal review, Plan creation, ready Missions, and finally a request for the next bounded action. Stop conditions never complete an Objective automatically, and untriaged evidence never becomes accepted support through evaluation.

## Considered options

- Persist Workspace Operational State as a state machine: rejected because operational conditions are projections of several concurrent facts and would become stale or combinatorial.
- Scatter nested conditionals through routes and workers: rejected because precedence, explanations, and completeness would be duplicated and difficult to audit.
- Adopt a general-purpose rules engine: rejected because the v1.1 rule set is small, ordered, code-reviewed, and benefits from static types rather than runtime rule configuration.

## Consequences

The decision table is the single pure policy interface used by API commands, Workspace projection, workers, and tests. Persistence, I/O, retries, and Agent cognition remain outside the evaluator. The validating TUI remains only on the throwaway `prototype/legal-next-step-engine` branch and is not production code.
