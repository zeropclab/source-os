# Discovery Agent State-Machine Prototype Verdict

Question: can the Discovery Agent revise collection from evidence without crossing approvals, and can a stopped objective be prevented from silently continuing?

## Verdict

Validated with the interactive prototype on `prototype/discovery-agent-state-machine`:

- Evidence may revise an Acquisition Plan inside the Approved Collection Boundary.
- A new source moves the Objective to `pending_approval`; planning cannot continue until the operator approves or rejects it.
- Need Hypothesis drafting requires a support Discovery Assessment that cites evidence; it never creates a Need Issue.
- A blocked Objective rejects further collection.
- A blocked Objective cannot be reopened by a reset. Only an Operator Boundary Revision that changes a versioned boundary can reactivate it.

## Rejected model

`blocked → reopen → active` was rejected because the objective could appear active while its exhausted boundary still prohibited useful work.

## Next

Formal implementation must model Objective status, versioned boundaries, plans, assessments, hypothesis drafts, and legal transitions. The TUI is a throwaway primary source and is not production code.
