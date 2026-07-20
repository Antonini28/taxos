# Phase 2 — Enterprise System Architecture

**Product:** Enterprise Agentic Tax Operating System (TaxOS)
**Status:** Complete — awaiting stakeholder review
**Inputs:** Phase 1 discovery (`docs/discovery/`), fixed architectural principles AP-1..AP-5 (below)
**Last updated:** 2026-07-20

## Fixed architectural principles (stakeholder-approved)

| ID | Principle |
|----|-----------|
| AP-1 | MVP is one production-quality vertical slice: the governed UK VAT lifecycle |
| AP-2 | Deterministic, versioned, reproducible computation core — LLMs never calculate tax |
| AP-3 | UK/HMRC first; jurisdictions as modular content packs, no core changes to add one |
| AP-4 | Every significant decision justified with trade-offs and recorded as an ADR |
| AP-5 | Cloud-native, modular, event-driven, production-grade — Big Four deployable |

## Document map

| # | Document | Covers |
|---|----------|--------|
| 01 | [Architecture Overview & Context](01-architecture-overview.md) | C4 L1 context diagram, architectural style decision, quality-attribute drivers |
| 02 | [Container Architecture](02-container-architecture.md) | C4 L2, every runtime container, technology mapping, communication matrix |
| 03 | [Component Architecture](03-component-architecture.md) | C4 L3 for the three core services, module boundaries, dependency rules |
| 04 | [Data Architecture](04-data-architecture.md) | Database design (ERD), lineage model, caching strategy, object storage, retention |
| 05 | [Eventing & Asynchronous Processing](05-eventing-and-async.md) | Event-driven backbone, message queues, task scheduling, WebSockets |
| 06 | [API Design](06-api-design.md) | Gateway, REST standards, versioning, rate limiting, OpenAPI, GraphQL position |
| 07 | [Security Architecture](07-security-architecture.md) | AuthN/AuthZ (RBAC+ABAC), secrets, tenancy isolation, audit chain (deep dive in Phase 9) |
| 08 | [Deployment & Cloud Architecture](08-deployment-and-cloud.md) | Azure deployment diagram, environments, HA, DR, CI/CD, IaC, feature flags |
| 09 | [Observability](09-observability.md) | Logging, metrics, tracing, SLOs, agent-specific telemetry |
| 10 | [Sequence Diagrams & Agent Communication](10-sequence-diagrams.md) | Key runtime flows incl. agent orchestration and approval gates |
| — | [ADR log](adr/) | ADR-001 … ADR-012 |

## ADR index

| ADR | Decision | Status |
|-----|----------|--------|
| [001](adr/ADR-001-modular-monolith-with-satellite-services.md) | Modular monolith core with satellite services (not fine-grained microservices) | Accepted |
| [002](adr/ADR-002-postgresql-system-of-record.md) | PostgreSQL as single system of record; pgvector for embeddings at MVP | Accepted |
| [003](adr/ADR-003-event-backbone-outbox.md) | Transactional outbox + broker-abstracted event bus (Redis Streams dev / Azure Service Bus prod) | Accepted |
| [004](adr/ADR-004-docs-as-code-c4.md) | C4 model + Mermaid docs-as-code for all architecture documentation | Accepted |
| [005](adr/ADR-005-rule-engine-content-packs.md) | Deterministic rule engine with versioned jurisdiction content packs | Accepted |
| [006](adr/ADR-006-multitenancy-rls.md) | Multi-tenancy via shared database + PostgreSQL row-level security | Accepted |
| [007](adr/ADR-007-identity-oidc-jwt-rbac-abac.md) | OIDC (Entra ID) + JWT; layered RBAC + ABAC authorisation | Accepted |
| [008](adr/ADR-008-azure-container-apps.md) | Azure Container Apps over AKS for MVP compute | Accepted |
| [009](adr/ADR-009-audit-log-hash-chain.md) | Append-only audit log with hash chaining in PostgreSQL | Accepted |
| [010](adr/ADR-010-rest-first-api.md) | REST-first API; GraphQL deferred to a read-gateway need, not adopted by default | Accepted |
| [011](adr/ADR-011-caching-strategy.md) | Redis cache-aside + precomputed reporting aggregates | Accepted |
| [012](adr/ADR-012-agent-runtime-isolation.md) | Agent runtime as an isolated service with tool allow-list boundary | Accepted |
| [013](adr/ADR-013-langgraph.md) | LangGraph as the agent orchestration framework (Phase 3) | Accepted |
| [014](adr/ADR-014-knowledge-graph-strategy.md) | Knowledge graph: relational-first, Neo4j behind a proven-need gate (Phase 4) | Accepted |
| [015](adr/ADR-015-hybrid-retrieval.md) | Hybrid retrieval: RRF fusion + cross-encoder reranking (Phase 4) | Accepted |
| [016](adr/ADR-016-mlflow-registry.md) | MLflow registry + Celery pipelines-as-code for the ML lifecycle (Phase 5) | Accepted |
| [017](adr/ADR-017-anomaly-detection-strategy.md) | Anomaly detection: rules + per-population Isolation Forest; autoencoder gated (Phase 5) | Accepted |
| [018](adr/ADR-018-github-actions.md) | GitHub Actions for CI/CD; Azure DevOps mapped, not adopted (Phase 8) | Accepted |

*Note:* ADR-001..012 were authored in Phase 2; the log is continuous across phases (013 from Phase 3, 014–015 from Phase 4). ADR-012 fixed the architectural seam in advance so ADR-013's framework choice could not leak into the core.
