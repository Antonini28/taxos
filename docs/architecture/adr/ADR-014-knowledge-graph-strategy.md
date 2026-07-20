# ADR-014 — Knowledge graph: relational-first with a pre-committed Neo4j adoption gate

**Status:** Accepted · 2026-07-20 · Principles: AP-4, AP-5; FR-405 · Full analysis: `docs/knowledge/04-knowledge-graph.md`

## Context
FR-405 calls for a knowledge graph supporting multi-hop questions (regulatory change → affected obligations; entity → counterparty → jurisdiction → registration gaps). The brief names Neo4j. Inventorying the actual target queries shows most hops traverse **structured operational data already in PostgreSQL with foreign keys and RLS** — not free text — and the known query set is fixed-shape, 3–5 hops.

## Decision
1. **R2–R3:** graph as first-class PostgreSQL edge tables (`kg_edge` with kind, temporal validity, provenance) + views exposing existing FKs as virtual edges; populated by pack publication (rule→source citations), corpus ingestion (interprets/supersedes), and masterdata.
2. Traversals ship as **named, tested query functions** exposed as Tool Gateway tools (`affected_obligations`, `registration_gaps`, …) — semantic capabilities, not an open query surface (ADR-012 consistency).
3. **R4 gate:** adopt **Neo4j (AuraDB)** when a trigger fires: (a) required traversal is variable-depth/pattern-shaped beyond recursive-CTE ergonomics, or (b) measured graph-query load strains Postgres. The adoption design is pre-committed (projection via existing outbox events; §2 node/edge model unchanged; per-tenant databases mirroring ADR-006's premium path) so adoption is execution, not research.
4. GraphRAG enrichments (citation-neighbourhood expansion, impact-aware ranking, supersession warnings) land behind the `Retriever` port only on measured `research-qa` improvement.

## Alternatives
- **Neo4j from day one** — rejected: a second stateful store + CDC sync pipeline + re-implemented tenant isolation, maintained to answer queries Postgres already answers; classic résumé-driven architecture. The seam (named-query tools) makes deferral cheap and reversal costless to callers.
- **Apache AGE (Cypher in Postgres)** — same-DB appeal, but extension availability/maturity on Azure Flexible Server is a platform risk we don't need for fixed-shape queries.
- **No graph (pure RAG)** — fails the enumerated multi-hop questions; impact analysis (Regulatory Monitor's `get_pack_citations` reverse index) inherently needs edges.

## Consequences
- (+) FR-405 capability ships in R2–R3 with zero new infrastructure; every edge carries provenance + temporal validity like the rest of the platform.
- (+) Agents/tools are store-agnostic — the Neo4j migration (if triggered) changes implementations behind named queries only.
- (−) Variable-depth exploratory graph queries are not ergonomic until/unless Neo4j lands → accepted; no current requirement needs them, and the trigger is defined.
- (−) Edge tables add ingestion/publication write paths → covered by the same event-driven projection machinery as `rpt_*` aggregates (ADR-011 pattern).
