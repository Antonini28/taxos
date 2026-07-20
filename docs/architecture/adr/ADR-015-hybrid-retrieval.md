# ADR-015 — Hybrid retrieval: RRF fusion + cross-encoder reranking; deterministic query processing

**Status:** Accepted · 2026-07-20 · Principles: AP-2 (mindset), GP-3; FR-402/403, NFR-07 · Full design: `docs/knowledge/03-retrieval.md`

## Context
GP-3 makes retrieval quality load-bearing: the ≥95% citation-support target (NFR-07) decomposes into retrieval recall (gold passage present in context) × generation faithfulness. Tax queries mix semantic questions ("can we recover input VAT on…") with exact-identifier lookups ("VIT13500", "s.26(3)") — the classic case where neither vectors nor keywords alone suffice.

## Decision
1. **Parallel vector (pgvector HNSW) + keyword (Postgres FTS + trigram)** searches under identical metadata filters (tenant, jurisdiction, tax_domain, temporal as-of, authority rank) applied *in-store*.
2. **Reciprocal Rank Fusion (k=60)** to merge; rank-based, no score normalisation.
3. **Cross-encoder reranker** (managed or small local model behind a `Reranker` port), top-40 → top-8.
4. **Deterministic query processing:** curated statutory-synonym table for expansion; sub-query decomposition is the Research agent's job (traced, budgeted), not hidden in the retrieval layer. No runtime LLM query rewriting.
5. **Coverage diagnostics** on every result — the evidence for INSUFFICIENT_SOURCES verdicts (FR-403).
6. Retrieval is uncached; index generations are versioned and cut over only on eval non-regression (embedding-model upgrades never re-embed in place).

## Alternatives
- **Vector-only + bigger k** — misses exact-identifier queries (measured failure class in any legal-domain benchmark); keyword side is nearly free in Postgres.
- **Score-normalised weighted fusion** — weights drift as corpus grows; RRF is parameter-light and robust (the reason it's the industry default).
- **LLM-as-reranker** — ~10× cost/latency at our k for marginal nDCG gain; cross-encoders are the right tool.
- **Runtime LLM query expansion** — non-deterministic retrieval breaks eval reproducibility and produces "same question, different answer" reviewer-trust failures; offline LLM-assisted synonym authoring captures the benefit governably.
- **External search engine (Elasticsearch)** — duplicate stateful infrastructure vs FTS at MVP scale (ADR-002 consolidation); Azure AI Search remains the enterprise swap behind the `Retriever` port.

## Consequences
- (+) Both retrieval failure classes (semantic drift, identifier miss) covered; deterministic pipeline ⇒ reproducible evals and stable reviewer experience.
- (+) Ports (`Retriever`, `Reranker`) keep store/model choices two-way doors with CI-gated swaps.
- (−) Reranker adds ~400ms p95 and a model dependency → within the 700ms tool budget; degradation path defined (serve RRF order flagged `unreranked`, widen k).
- (−) Synonym table is a curated asset needing ownership → assigned to corpus governance (doc 01 §4) with eval-driven gap detection.
