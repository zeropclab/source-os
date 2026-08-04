# PROTOTYPE — Legal Next Step engine

This throwaway logic prototype answers one question: can a pure, ordered decision table derive one explainable Workspace Operational State and Legal Next Step from current facts more reliably than a persisted UI state machine or conditionals spread across callers?

It deliberately has no database, API, Agent runtime, tests, or production error handling. Drive contradictory and changing facts by hand and watch the complete input snapshot, matched rule, trace, and alternate-evaluator comparison after every action.

Run from the repository root:

```bash
uv run sourceos-prototype-legal-next-step
```

The prototype is evidence for the architecture decision. It is not production code and must not be merged into `main`.
