# ADR-002 — PostgreSQL as single system of record (pgvector at MVP)

**Status:** Accepted · 2026-07-20 · Principles: AP-2, AP-3, AP-5

## Context
The platform needs: relational integrity for financial data, row-level security for tenancy, JSONB for computation snapshots/raw payloads, partitioning for transaction volume, full-text + vector search for the R2 knowledge layer, and append-only guarantees for audit. Options: one engine covering all, or a polyglot estate (relational + dedicated vector DB + document store).

## Decision
**PostgreSQL 16** (Azure Database for PostgreSQL Flexible Server) is the single system of record: business data, workflow, audit chain, agent traces, ML metadata, and — at MVP scale — embeddings via **pgvector** (HNSW) combined with Postgres FTS for hybrid retrieval. Redis and Blob are auxiliary (rebuildable / raw artifacts).

## Alternatives considered
1. **SQL Server / Azure SQL** — capable, but RLS is clunkier, JSONB-equivalent weaker, pgvector has no first-class analogue, licensing cost non-zero, and the Python ecosystem (SQLAlchemy/Alembic maturity) favours Postgres.
2. **Cosmos DB** — no relational integrity for financial lineage joins; RU cost model punishes analytical scans; rejected for the system of record.
3. **Dedicated vector DB (Qdrant/Pinecone/Weaviate) from day one** — an extra stateful service, another security/tenancy/backup story, for a corpus (thousands–low-millions of chunks) pgvector handles comfortably. Retrieval sits behind a `Retriever` interface; the swap to **Azure AI Search** is a planned enterprise-tier option (doc 04 §7), not a rewrite.
4. **Event sourcing as the storage model** — maximal auditability but a large complexity tax (projections, replay ops, developer ramp). The audit hash chain + immutable snapshots deliver the *evidence* property without re-platforming the entire domain (see ADR-009).

## Consequences
- (+) One backup/DR/tenancy/security story; RLS gives database-enforced isolation; SQL joins power lineage drill-down cheaply.
- (+) Fewer moving parts = credible ops for a small team (AP-5's "production-grade" includes "operable").
- (−) Postgres becomes the scaling bottleneck first → mitigations sequenced in doc 04 §7 (partitioning now; replicas, AI Search, per-tenant DBs later).
- (−) pgvector recall/latency ceilings at large corpus scale → accepted consciously; the interface seam caps the migration cost.
