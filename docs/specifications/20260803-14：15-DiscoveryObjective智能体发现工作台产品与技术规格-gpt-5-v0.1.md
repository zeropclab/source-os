# Discovery Objective 智能体发现工作台：产品与技术规格

## Problem Statement

SourceOS 当前以人工创建 `Acquisition Mission`、独立运行 worker、Pi 仅对固定证据包提出建议的传统 Web 工作流组织能力。经营者无法把一个长期现实不确定性作为 Agent 的持续工作对象，也无法审阅 Agent 为什么改变采集计划、是否越过批准边界、何时应停止，以及后来产品结果是否校正了最初判断。

经营者需要一个以 `Discovery Objective` 为中心的工作台：让 Discovery Agent 在明确的批准边界内自主采集、补全上下文、寻找反证与修订计划；让不可逆或扩大权限的动作明确等待经营者批准；让每一个结论保留证据链，而不把模型输出伪装成真实需求、付费或利润。

## Solution

引入 `Discovery Objective Workspace` 作为 SourceOS 首版 Agent 产品的主界面和 API 聚合边界。经营者创建一个可证伪的 Discovery Objective 与初始 Approved Collection Boundary；Discovery Agent 生成版本化 Acquisition Plan，并在边界内驱动具体 Acquisition Mission 与 Run。每轮运行后它持久化 Evidence Candidate、Discovery Assessment、Need Hypothesis 草案与 Plan Revision；工作台呈现当前判断、最强反证、未知项、边界、待批准请求与合法下一步。

Agent 仅能执行已批准公开信源内、受工具/请求/时间/成本约束的动作。它不能自动扩源、使用凭证、增加预算、联系任何人、创建 Need Issue、创建 Product Thesis、开发、发布、销售或收款。被阻塞的 Objective 不能裸重开；经营者必须创建有明确理由和增量的 Operator Boundary Revision，才能激活下一版计划。

## User Stories

1. As a solo operator, I want to create a falsifiable Discovery Objective, so that a long-lived business uncertainty is not confused with one collection job.
2. As a solo operator, I want to state objective-level resource, evidence, and decision stop conditions, so that the Agent cannot research indefinitely.
3. As a solo operator, I want to define an Approved Collection Boundary with approved public sources, allowlisted tools, and limits, so that autonomous collection remains reversible.
4. As a solo operator, I want to see the boundary version that governed every plan and run, so that I can audit what the Agent was allowed to do at that time.
5. As a Discovery Agent, I want to create an Acquisition Plan version with its question, source selection, counterevidence target, and bounded missions, so that my proposed action is reviewable before or after execution.
6. As a Discovery Agent, I want to revise a plan after evidence reveals repetition, weak independence, or missing context, so that I can adapt without silently changing scope.
7. As a solo operator, I want every Plan Revision to show its predecessor and cited reason, so that I can distinguish learning from arbitrary retuning.
8. As a Discovery Agent, I want to create and execute an Acquisition Mission only within the current approved boundary, so that I cannot expand collection authority implicitly.
9. As a solo operator, I want existing Mission Runs and their raw artifacts to remain immutable and linked to the Objective and Plan, so that results remain reproducible.
10. As a solo operator, I want candidate evidence to retain original material, context, source URI, lineage, and run linkage, so that I can inspect what the Agent actually observed.
11. As a Discovery Agent, I want to emit a Discovery Assessment containing support, counterevidence, unknowns, coverage gaps, and a next-plan recommendation, so that a conclusion is separable from evidence.
12. As a solo operator, I want an Assessment to cite evidence IDs explicitly, so that a persuasive narrative without evidence cannot drive the Objective.
13. As a Discovery Agent, I want to draft a Need Hypothesis only when a support Assessment cites evidence, so that a hypothesis cannot appear from an uncited model assertion.
14. As a solo operator, I want Need Hypotheses to remain drafts until I explicitly promote one, so that the system never auto-creates a Need Issue.
15. As a solo operator, I want a requested new source, credential, tool, budget, time extension, or external action to appear as an Operator Approval, so that I control boundary expansion.
16. As a solo operator, I want to approve or reject a requested boundary change with a reason, so that the decision is auditable and the Agent receives a clear next state.
17. As a solo operator, I want a blocked Objective to reject all further Agent collection or planning actions, so that “stopped” is enforced rather than decorative UI text.
18. As a solo operator, I want to reactivate a blocked Objective only through an Operator Boundary Revision that records a concrete new allowance, so that a restart has actual capacity to act.
19. As a solo operator, I want to see a Blocked Assessment with the exact unknown, exhausted constraint, and required new approval, so that I know what I must decide rather than seeing “no result.”
20. As a solo operator, I want the Workspace to center the current Assessment, strongest counterevidence, unknowns, active plan, running actions, evidence, and approvals, so that the Agent is controlled through an operating surface rather than chat alone.
21. As a solo operator, I want chat or free-form instruction to remain secondary and unable to bypass the Workspace controls, so that natural-language interaction cannot evade permissions.
22. As a solo operator, I want to close an Objective as promoted, rewritten, abandoned, or blocked, so that every discovery loop has an explicit decision state.
23. As a solo operator, I want a Discovery Decision Record at closure, so that I can revisit the decision with cited support, counterevidence, resource use, and unresolved unknowns.
24. As a solo operator, I want to attach later Outcome Feedback from product tracking, delivery, retention, payment, refund, or support, so that later reality calibrates discovery without being mistaken for automatic market proof.
25. As a solo operator, I want to see that collection counts and model activity are telemetry rather than Agent accuracy, so that the product does not create false confidence.
26. As a solo operator, I want existing Evidence Inbox, Need Issue, Product Thesis, Feature, and Delivery flows to remain available, so that the Agent layer evolves the product instead of discarding proven audit paths.

## Implementation Decisions

- Add durable domain entities: `DiscoveryObjective`, versioned `ApprovedCollectionBoundary`, versioned `AcquisitionPlan`, `PlanRevision`, `DiscoveryAssessment`, `NeedHypothesis`, `OperatorApproval`, `OperatorBoundaryRevision`, and `DiscoveryDecisionRecord`.
- `DiscoveryObjective` owns the falsifiable question, operator-defined stop conditions, lifecycle status, and current boundary/plan references. `AcquisitionMission` remains a concrete bounded instruction, but belongs to an Acquisition Plan rather than acting as the top-level discovery object.
- Objective lifecycle states are `active`, `pending_approval`, `blocked`, and `completed`. Legal transitions are restricted to:

  ```text
  active → pending_approval → active
  active → blocked | completed
  blocked → OperatorBoundaryRevision → active
  completed → terminal
  ```

  This state machine is validated by the throwaway `prototype/discovery-agent-state-machine` branch; a bare reopen transition is forbidden.
- A Boundary Revision is versioned and must name a material delta: source, tool, request budget, time budget, cost budget, or evidence condition. It retains a reason and operator attribution; only it may reactivate a blocked Objective.
- Discovery Agent runtime is a bounded orchestrator. It receives Objective state and a read-only evidence bundle, returns structured proposals and Assessments, and invokes only allowlisted collection/context-repair tools inside the current boundary. It never receives unrestricted database authority.
- Existing Pi proposal runtime is retained as a lower-level cognitive component but no longer represents the product’s full Agent model. The orchestration layer validates proposed actions, records tool audit events, creates allowed plans/missions, and refuses illegal transitions before a worker executes anything.
- Existing source configuration versions, mission-run queues, cancellation checkpoints, raw artifacts, candidate signal lineage, Evidence Inbox triage, Need Issue promotion, Product Thesis, Feature, Delivery, and Outcome controls remain source-of-truth integrations. New models reference them by immutable IDs; they do not duplicate raw evidence.
- `DiscoveryAssessment` has kind(s) for support, counterevidence, coverage gap, unknown, blocked, and decision recommendation. Every non-empty conclusion cites evidence or prior Assessments; a Need Hypothesis requires at least one cited support Assessment.
- `NeedHypothesis` is distinct from a Need Issue. Promotion is an explicit operator endpoint/action and reuses the existing Need Issue evidence workflow; no Agent endpoint creates a Need Issue, Product Thesis, feature, delivery record, or external action automatically.
- The primary public API seam is a Discovery Objective Workspace resource: create/read Objective, retrieve a single workspace projection, submit bounded Agent planning/execution requests, record/review approvals, create Boundary Revisions, list Assessments/Hypotheses, and close the Objective with a Decision Record. Existing Mission and Evidence APIs remain lower-level seams.
- The primary Web seam is a `Discovery Objective Workspace` route that reads the workspace projection and exposes only legal controls. The existing visual collection console becomes the plan/run area inside this page; it is not discarded.
- Workspace ordering is fixed by decision significance: objective and stop conditions; current Assessment, strongest counterevidence and unknowns; current Plan Revision; running/queued Missions; evidence; approvals; closure/Outcome Feedback. Chat is a secondary inspection/control aid, never the authority boundary.
- Outcome Feedback is append-only, linked to a closed Decision Record, and intentionally does not generate a global Agent accuracy metric. It supports later calibration views only after real product/service outcomes exist.

## Testing Decisions

- Tests verify public behaviour and legal transitions, never ORM internals, prompt wording, or private helper calls.
- Primary API seam: Discovery Objective Workspace endpoints. Tests must prove creation, workspace projection, allowed plan revision, denied out-of-bound action, approval/rejection, block, Boundary Revision reactivation, hypothesis evidence requirement, promotion boundary, closure, and append-only Outcome Feedback.
- Primary Web seam: the Workspace route must expose the current decision state, cited evidence links, pending approvals, disabled/absent illegal actions, and the existing collection console as the plan/run region.
- Existing mission-run API tests are prior art for bounded execution, durable queues, cancellation, replay, raw artifact lineage, and retry. Existing Agent Run API tests are prior art for immutable evidence bundles, idempotency, budgets, runtime failure, and operator decisions. Existing web workbench tests are prior art for stable HTML controls and public endpoint links.
- State-machine cases from the prototype become behavioural tests: repeated source causes a cited plan revision; pending approval prevents further planning/execution; a new source cannot be used before approval; blocked rejects actions; only Boundary Revision restores capacity; a Need Hypothesis without cited support is rejected; later Outcome Feedback does not alter original evidence.
- Migration tests create a fresh database and prove all legacy Mission/Run/Evidence/Need records remain queryable and linkable after the new Objective layer is introduced.

## Out of Scope

- Autonomous external contact, interviews, sales, marketing, publishing, payment collection, pricing, product release, code generation, PR creation, or merge authority.
- Credentialed/subscription source access without a separately approved boundary and implementation.
- A chat-first autonomous founder interface.
- A global Agent accuracy, profitability, or market-demand score before sufficient real Outcome Feedback exists.
- Replacing existing source adapters or adding broad multi-platform collection in this feature.
- Migrating historical Missions into Objectives automatically; legacy records remain accessible and can be attached deliberately where appropriate.

## Further Notes

- The design decisions are captured in ADR-0001 through ADR-0009 and the root domain glossary.
- The primary source for legal transition behaviour is the throwaway prototype branch `prototype/discovery-agent-state-machine`, especially its verdict document. The TUI must not ship as production code.
- This specification establishes the first Agent loop only: discover and judge. Product delivery and commercial operations are feedback inputs, not Agent-owned actions in this scope.
