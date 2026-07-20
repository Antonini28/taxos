# Phase 4 — Knowledge Management (Enterprise RAG)

**Product:** Enterprise Agentic Tax Operating System (TaxOS)
**Status:** Complete — awaiting stakeholder review
**Inputs:** FR-401..405 (knowledge requirements), NFR-07 (≥95% citation support), Research agent spec (docs/ai/04 §4.2), ADR-002 (pgvector), principles GP-3 (cited AI only), AP-3 (content packs)
**Last updated:** 2026-07-20

## Design goal

> Every tax-technical statement the platform makes must be traceable to an authoritative, versioned, temporally-valid source — and when the corpus cannot support an answer, the platform must say so.

RAG here is not a chatbot feature; it is the **evidence supply chain** for the Research agent, the domain agents' judgement flags, the Regulatory Monitor, and ultimately the citations that appear in review packages and evidence packs.

## Document map

| # | Document | Covers |
|---|----------|--------|
| 01 | [Corpus & Ingestion](01-corpus-and-ingestion.md) | Source taxonomy + authority ranking, temporal validity, ingestion pipelines (HMRC/OECD/legislation/internal/SharePoint/email), corpus governance |
| 02 | [Chunking & Embedding](02-chunking-and-embedding.md) | Structure-aware chunking per document class, embedding strategy, metadata schema |
| 03 | [Retrieval](03-retrieval.md) | Hybrid search (vector + BM25 + metadata), fusion, reranking, query pipeline, evaluation |
| 04 | [Knowledge Graph](04-knowledge-graph.md) | Graph model design, Neo4j evaluation, phased adoption (→ ADR-014) |
| 05 | [Citations & Grounding](05-citations-and-grounding.md) | Citation generation, source validation, the hallucination-prevention stack |
| — | [ADR-014](../architecture/adr/ADR-014-knowledge-graph-strategy.md) | Knowledge graph: relational-first, Neo4j at proven multi-hop need |
| — | [ADR-015](../architecture/adr/ADR-015-hybrid-retrieval.md) | Hybrid retrieval with RRF fusion + cross-encoder reranking |

## Non-negotiables inherited from earlier phases

- Retrieval is a **tool** behind the Tool Gateway (`search_knowledge`) — agents cannot query stores directly (ADR-012).
- The corpus is **governed content**: versioned, provenance-tracked, reviewed on ingest — the same discipline as rule packs (ADR-005). An ungoverned corpus is a prompt-injection delivery vehicle (doc 07 §3).
- Retrieval interfaces are **implementation-hiding** (`Retriever` port): pgvector at MVP, Azure AI Search as the enterprise swap (ADR-002) — nothing in this phase may leak store specifics upward.
- UK-first corpus depth; source taxonomy and metadata schema designed for multi-jurisdiction from day one (AP-3).
