# ADR-011 — Caching: Redis cache-aside + event-invalidated reporting aggregates

**Status:** Accepted · 2026-07-20 · Principles: AP-5; NFR-06

## Context
Dashboard p95 < 500ms over partitioned transaction tables requires precomputation; authz context lookup happens on every request; but this is a *compliance* platform — a stale approval state or workflow state shown as current is a correctness bug, not a performance win.

## Decision
Three layers (doc 04 §4): HTTP ETags (short), Redis cache-aside for authz context + reference data + dashboard aggregates (event-driven invalidation + TTL backstop), and Postgres `rpt_*` aggregate tables incrementally maintained by a worker projector consuming domain events. **Never cached:** workflow state, approvals, anything on a write-decision path — those read the system of record every time.

## Alternatives considered
1. **Materialized views with scheduled REFRESH** — simple but whole-view refresh is too coarse (minutes of staleness or heavy refresh load); event-driven incremental projection gives seconds-fresh aggregates at row-level cost.
2. **Read-through caching library / second-level ORM cache** — invisible caching on entities is precisely how stale-state correctness bugs happen in workflow systems; caching stays explicit and allow-listed by object type.
3. **CDN/edge caching of API responses** — dashboards are per-tenant, per-scope private data; edge cache keys would have to include auth context — high leak risk for negligible gain (SSR + Redis already meet the SLO). Static assets only at the CDN.
4. **In-process memory caches** — multi-replica invalidation storms; Redis centralises invalidation; tiny per-request memoisation only.

## Consequences
- (+) SLOs achievable with boring, debuggable machinery; every cache key carries tenant (no cross-tenant bleed, ADR-006 alignment).
- (+) Aggregates are rebuildable from source (nightly verification job heals drift — doc 05 §4).
- (−) Event-driven invalidation adds consumer code per cached family → the invalidation map is documented next to the event catalogue and tested (stale-read integration tests assert invalidation on `ComputationCompleted`/`ApprovalGranted`).
- (−) Projector lag (~seconds) means dashboards trail reality slightly → acceptable and honest: dashboards show `as_of` timestamps.
