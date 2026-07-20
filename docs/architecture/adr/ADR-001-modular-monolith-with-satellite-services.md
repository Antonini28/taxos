# ADR-001 — Modular monolith core with satellite services

**Status:** Accepted · 2026-07-20 · Supersedes: — · Principles: AP-4, AP-5

## Context
The master brief calls for "microservices". A literal reading (service per domain: ingestion-svc, vat-svc, workflow-svc, …) would create 8–10 deployables sharing one transactional dataset, operated by a very small team. The dominant quality drivers (doc 01 §1) are auditability, transactional correctness (audit + state + outbox atomicity), and operability — all of which distributed transactions make harder.

## Decision
Three application deployables: **taxos-api** (strictly modularised monolith owning all transactional domain logic), **taxos-agents** (isolated LLM/agent runtime), **taxos-workers** (async execution of the same domain codebase). Module boundaries inside taxos-api are enforced by import-linter contracts, published service interfaces, and domain events — every module is service-extraction-ready.

## Alternatives considered
1. **Fine-grained microservices** — Rejected for now: distributed transactions across audit/state/outbox, N× infra cost, N× pipelines, network-partition failure modes, and no current scaling driver that differs per domain module. The industry consensus (Fowler's "MonolithFirst", Microsoft's own modular-monolith guidance, Shopify/Stack Overflow precedents) is that premature decomposition is the leading cause of failed microservice estates.
2. **Pure single monolith (agents in-process)** — Rejected: the agent workload has a genuinely different scaling profile (bursty, scale-to-zero), dependency set (LLM SDKs — AP-2 wants them physically out of the core), security blast radius, and release cadence. That *is* a service boundary by every sensible criterion.
3. **Serverless functions (Azure Functions per operation)** — Rejected: cold-start on interactive paths, 10-minute-style limits vs long pipelines, and orchestration state sprawl; retained as an option for isolated event handlers later.

## Consequences
- (+) One transaction = state + audit + outbox; reproducibility and evidence guarantees are trivial to enforce.
- (+) Small-team operable; single migration history; single observability story.
- (+) Extraction path documented: a module graduates to a service when it gains an independent scaling/either-technology/organisational driver; its interface + events already exist.
- (−) Discipline required: module boundaries erode without enforcement → import-linter contracts are CI-blocking.
- (−) Whole-core deploys couple release cadence across modules (acceptable at this team size; revisit trigger: >2 teams or conflicting release cadences).
