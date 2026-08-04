---
status: accepted
---

# Build v1.1 as an agent-native modular monolith

SourceOS v1.1 will remain an Agent-native product, but deterministic authority belongs to a Discovery Orchestrator rather than the language model, HTTP routes, templates, or workers. The codebase will be a modular monolith with Discovery, Acquisition, and Productization modules; Pi, collection platforms, artifact storage, PostgreSQL, Web/API, and workers sit at explicit seams as adapters.

Discovery and Acquisition each own changes to their write models behind deep command interfaces. Operator actions and Agent proposals enter as commands, executions return immutable facts, and the Orchestrator reevaluates the Workspace Operational State and Legal Next Step. Cross-module callers do not modify ORM models directly. The Workspace is a live read projection over module-owned facts, not a second persisted source of truth in v1.1.

Agent Work and Acquisition Work are durable asynchronous jobs claimed by a worker, with boundary/input versions, budgets, idempotency, cancellation, retry, failure, and result facts. External adapters accept immutable assignments and return immutable results; they do not know about SQLAlchemy or manage transactions.

The deployment remains one FastAPI/Jinja Web/API process, one worker process, and PostgreSQL. Jinja is enhanced with HTMX for server-owned interactions, Alpine.js for local presentation state, and SSE for progress updates. Pi remains a replaceable Node runtime adapter. Redis, Kafka, microservices, a React/Next.js SPA, and a separately persisted Workspace read model are deferred until measured constraints justify their operational cost.

## Considered options

- Continue router-centric CRUD: rejected because lifecycle, permissions, versioning, and orchestration rules are already spreading across routers, workers, and templates.
- Split into microservices and a message bus: rejected because SourceOS is a single-operator product whose current scale does not justify distributed transactions, deployment, and observability overhead.
- Move to a client-owned SPA state model: rejected because server-side evidence, boundary, and lifecycle facts must remain authoritative and the extra frontend state would duplicate them.

## Consequences

Existing public seams remain compatible while router and worker logic moves behind module interfaces incrementally. PostgreSQL remains the transactional source of truth and durable queue. The core-engine prototype and persistence-model decision must conform to this module ownership and command-fact-reevaluation architecture.
