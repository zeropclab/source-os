# SourceOS

SourceOS is a personal operating system for turning traceable reality signals into product decisions. Its language separates evidence from claims and bounded agent action from operator authority.

## Agent Operation

**Discovery Agent**:
The bounded actor that plans and performs approved public-source collection, then returns traceable evidence, counterevidence, unknowns, and a proposed next action. It never makes product, commercial, or external-contact decisions.
_Avoid_: autonomous founder, full agent, chat assistant

**Operator Approval**:
The explicit decision by the operator that permits an action outside the Discovery Agent's approved source, tool, or budget boundary.
_Avoid_: confirmation, consent, automatic escalation

**Approved Collection Boundary**:
The versioned set of public sources, tools, request, time, and cost limits within which a Discovery Agent may act without a new Operator Approval.
_Avoid_: agent permission, unrestricted access

**Discovery Objective**:
The operator-owned, falsifiable question that gives a Discovery Agent a continuing reason to learn until its stop condition, pause, or budget limit is reached.
_Avoid_: project, research task, agent prompt

**Acquisition Plan**:
A versioned proposal from a Discovery Agent that states how one Discovery Objective should next be investigated, including sources, hypotheses, counterevidence targets, and bounded runs.
_Avoid_: mission, schedule, crawl configuration

**Plan Revision**:
A recorded change from one Acquisition Plan version to another that names the evidence or coverage gap responsible for the change. A revision may only use the current Approved Collection Boundary.
_Avoid_: retuning, silent optimization, agent learning

**Discovery Assessment**:
A versioned, evidence-cited Agent judgement about an Objective's support, counterevidence, unknowns, coverage gaps, and recommended next plan. It is not a business decision.
_Avoid_: answer, conclusion, validated result

**Need Hypothesis**:
An Agent-drafted, falsifiable explanation of a possible unmet need that awaits operator promotion to a Need Issue.
_Avoid_: discovered need, validated demand, product opportunity

**Blocked Assessment**:
A Discovery Assessment that states the Agent cannot produce a defensible next plan within the remaining evidence, boundary, and budget, and names the missing information or approval.
_Avoid_: failure, no result, keep researching

**Outcome Feedback**:
Observed tracking, delivery, retention, payment, refund, or support results from a product or service that the Discovery Agent may read to calibrate future discovery. It does not authorize the Agent to execute product or commercial actions.
_Avoid_: Agent action, market proof by itself

**Discovery Objective Workspace**:
The primary entry point and operator interface for one Discovery Objective. It presents its stop conditions, current Assessment, plan revisions, bounded runs, evidence, and approval decisions; the collection console is an operation area inside this flow, not a parallel top-level flow. It is not a chat-first interface.
_Avoid_: dashboard, task board, agent chat

**Legal Next Step**:
The single state-aware action that the Workspace recommends from an Objective's current lifecycle state, boundary, evidence gap, and stop conditions. It may be expanded into advanced controls, but it never bypasses the Approved Collection Boundary or Operator Approval.
_Avoid_: generic call to action, automatic escalation, workflow shortcut

**Workspace Operational State**:
A derived, non-persistent view of the current work inside a Discovery Objective, such as ready to plan, collecting, awaiting evidence review, awaiting Agent proposal review, or awaiting Operator Approval. It does not add lifecycle states to the Discovery Objective.
_Avoid_: Objective status, persisted UI stage, workflow state explosion

**Legal Next Step Priority**:
The fixed order that resolves competing Workspace Operational States: completed record and feedback; blocked boundary revision; pending approval decision; active run monitoring; evidence triage; Agent proposal review; lawful plan creation or review; then a new bounded collection proposal. It prioritizes permission and irreversibility before more work.
_Avoid_: arbitrary recommendation, parallel action overload, activity-first workflow

**Agent Proposal**:
A structured, evidence-cited recommendation or bounded collection action produced by the Discovery Agent. It may execute only inside the current Approved Collection Boundary; changing the Objective, Boundary, commercial record, or closure state remains an Operator decision.
_Avoid_: autonomous decision, silent background action, operator replacement

**Formal Record Promotion**:
The explicit Operator review action that converts an immutable Agent Proposal into a new formal Acquisition Plan Revision, Discovery Assessment, or Need Hypothesis. Rejection or a request for revision preserves the proposal and its reason without rewriting history.
_Avoid_: automatic persistence, silent overwrite, model-authored decision

**Closure Decision Required**:
A derived Workspace Operational State reached when a Discovery Objective meets a resource, evidence, or decision stop condition. It requires an Operator to write a Discovery Decision Record with promoted, rewritten, abandoned, or blocked outcome; only that record transitions the Objective to completed.
_Avoid_: automatic completion, stop condition as conclusion, silent termination

**Operator Workbench Visual Baseline**:
A desktop-first, high-information-density SourceOS operating surface: dark navigation, calm light work area, focused task/evidence/run columns, and prominent status, counterevidence, unknowns, and boundary risks. Visual polish serves judgment rather than decorative card feeds or mobile-first simplification.
_Avoid_: consumer dashboard, card stream, telemetry theatre

**Discovery Decision Record**:
The closing record for a Discovery Objective, stating its decision state, cited support and counterevidence, resource use, unresolved unknowns, and later Outcome Feedback. It is the unit through which discovery quality is revisited.
_Avoid_: agent score, success metric, final answer

**Acquisition Mission**:
A concrete, approved collection instruction within one Acquisition Plan; it directs a bounded run and is not evidence or a demand claim.
_Avoid_: discovery objective, task, crawl job

**Evidence Candidate**:
Traceable collected material awaiting operator triage; its existence does not establish a Need Issue or product demand.
_Avoid_: validated insight, discovered need

**Accepted Evidence**:
An Evidence Candidate explicitly retained through operator triage. It may support or counter a Discovery Assessment and a Need Hypothesis; an untriaged, ignored, or flagged candidate must retain its weaker or disqualifying status in every Agent proposal.
_Avoid_: raw collection, automatic proof, silent promotion
