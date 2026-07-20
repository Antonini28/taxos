# ADR-006 — Multi-tenancy: shared database with PostgreSQL row-level security

**Status:** Accepted · 2026-07-20 · Principles: AP-5; FR-703

## Context
Persona P6 (Big Four managed services) requires provable tenant isolation; MVP runs single-tenant but AP-5 demands the architecture not foreclose multi-tenancy. Isolation models: shared-schema RLS, schema-per-tenant, database-per-tenant, deployment-per-tenant.

## Decision
**Shared database, shared schema, `tenant_id NOT NULL` on every business table, PostgreSQL RLS policies enforced from migration 0001.** The application sets `SET LOCAL app.tenant_id` per transaction from the JWT claim; RLS policies filter every query; the app role has no BYPASSRLS. Isolation is verified by a dedicated cross-tenant attack test suite (R3 exit criterion). **Database-per-tenant** using identical migrations is the documented premium path for tenants with contractual isolation demands.

## Alternatives considered
1. **Application-level filtering only** — one forgotten WHERE clause = breach. Rejected: isolation must not depend on every developer being right every time.
2. **Schema-per-tenant** — migration fan-out (N schemas × Alembic), connection-pool fragmentation, painful cross-tenant ops (platform metrics), and it still shares the instance blast radius. The worst of both worlds at scale.
3. **Database-per-tenant from day one** — strongest isolation but N× cost/ops for a product with one tenant; retained as the premium tier because shared-schema code (RLS + tenant column) runs unchanged against a dedicated DB.
4. **Deployment-per-tenant** — the Big Four *do* sell this ("dedicated instance"); it is an ops/packaging option on top of this ADR (Terraform workspace per tenant), not a different architecture.

## Consequences
- (+) One migration history, one ops surface, marginal per-tenant cost ≈ zero; RLS gives database-enforced defence in depth under app bugs.
- (+) Tenant-keyed caches/WS filtering (docs 04/05) complete the isolation story beyond the DB.
- (−) RLS adds per-query planner overhead (~small; measured in load tests) and every index must lead with or include `tenant_id` — a design rule, enforced in migration review.
- (−) Noisy-neighbour risk on shared compute → per-tenant rate/ingestion limits (doc 06 §5) and the premium-tier escape hatch.
