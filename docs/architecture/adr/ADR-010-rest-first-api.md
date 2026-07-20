# ADR-010 — REST-first API; GraphQL deferred behind an explicit revisit trigger

**Status:** Accepted · 2026-07-20 · Principles: AP-4, AP-5; FR-706

## Context
The master brief lists REST, GraphQL, and OpenAPI. The real question is whether GraphQL earns its complexity on a governance-heavy platform with (initially) one first-party client.

## Decision
REST-first (conventions in doc 06) with contract-first OpenAPI 3.1 as the artifact of record; dashboard aggregation needs served by purpose-built read endpoints over precomputed `rpt_*` aggregates. GraphQL is **deferred**, with a recorded adoption shape and trigger rather than a vague "maybe".

## Alternatives considered
1. **GraphQL-first** — client-shaped queries and single-round-trip composition are real benefits, but the costs land on our riskiest surfaces: field-level authorisation on top of RBAC+ABAC+RLS (every resolver a potential leak), query cost/depth control (DoS surface), cache fragmentation (per-query shapes defeat the Redis aggregate strategy), N+1 discipline, and a second contract toolchain (SDL vs OpenAPI) to govern. For one web client whose heavy reads are dashboard aggregates we control, purpose-built endpoints are simpler *and* faster (server-side aggregation beats resolver composition).
2. **Hybrid now (GraphQL read-only BFF)** — the correct *shape* if adopted, but premature with one client; carrying two API paradigms from day one dilutes the contract-first discipline.
3. **gRPC for internal service calls** — only two internal sync paths exist (agents→ToolGateway); HTTP+OpenAPI keeps one contract technology and human-debuggable traffic. Revisit if service count grows post-extraction (ADR-001).

## Adoption trigger (recorded)
Introduce a **read-only GraphQL BFF** over the module service interfaces when ≥3 distinct client applications (e.g. web app + mobile + partner portal) demand differently-shaped reads of the same domains. Mutations remain REST forever (idempotency keys, ETags, and approval semantics are mature there).

## Consequences
- (+) One contract toolchain: spectral lint, schemathesis fuzzing, generated TS types (doc 06 §4) — cheap, high-assurance.
- (+) AuthZ surface stays enumerable — a security review can read the route list.
- (−) Frontend occasionally needs an endpoint added rather than self-serving a new query shape → accepted; endpoint addition is a small PR with review, which for this product is a governance feature, not friction.
