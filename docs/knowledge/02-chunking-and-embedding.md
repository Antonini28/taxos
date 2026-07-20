# 02 — Chunking & Embedding

## 1. Chunking philosophy

Chunking is **structure-aware, not size-driven**: tax sources have meaningful units (a manual paragraph, a legislative section, a policy clause), and the citation model (doc 05) requires chunks that map 1:1 to citable units. Fixed-size sliding windows are the baseline we explicitly reject for A-class content — a chunk that straddles two manual paragraphs produces citations that point at nothing.

## 2. Strategy per document class

| Class | Unit of chunking | Size handling | Context enrichment |
|---|---|---|---|
| Legislation (XML) | Section / subsection | Long sections split at subsection boundaries; never mid-provision | Prepend ancestry path: *"VATA 1994 › Part II › s.26 › (3)"* + cross-reference list |
| HMRC manuals (HTML) | Manual paragraph (natural citable unit, e.g. `VIT13500`) | Paragraphs are naturally sized; oversize ones split at heading breaks with `part 1/2` markers | Prepend: manual code, page title, heading chain; sibling-paragraph refs stored as metadata (not text) |
| OECD / IFRS (PDF) | Numbered paragraph / article | Layout-aware parse → paragraph tree; tables extracted separately (below) | Chapter/article ancestry; commentary linked to the article it comments |
| Internal policy (DOCX) | Heading-delimited clause | Split at H2/H3; max ~800 tokens with 10% overlap *only* within a clause | Doc title, section chain, tenant, policy owner, effective date |
| Corporate docs / memos | Semantic sections (heading detection + layout) | ~800 tokens, overlap within section | Doc type, parties, dates from Document-agent extraction |
| Emails (curated) | Message (thread-position aware) | Long threads: per-message chunks + a thread summary chunk (marked `derived`) | From/to roles (pseudonymised), date, subject, thread ref |
| **Tables** (all classes) | Table = its own chunk, serialised as Markdown + a generated natural-language summary line | Never split rows from headers | Caption + surrounding paragraph ref |

Derived chunks (thread summaries, table summaries) are always marked `derived: true` and cite their constituent source chunks — a derived chunk can never be a *terminal* citation (doc 05 §2 resolves it to its sources).

## 3. Chunk metadata schema

```python
class KnowledgeChunk(BaseModel):
    chunk_id: UUID
    doc_id: UUID                     # → knowledge_doc (provenance, version chain)
    tenant_id: UUID | None           # None = global A-class corpus
    # --- retrieval filters (indexed columns, not JSON) ---
    authority_rank: Literal["A1","A2","A3","A4","B1","B2","B3"]
    jurisdiction: str                # "UK", "OECD", ... (AP-3)
    tax_domain: list[str]            # ["VAT"], ["CT","TP"], ...
    valid_from: date; valid_to: date | None
    license_class: str
    derived: bool
    # --- citation identity (doc 05) ---
    citation_ref: CitationRef        # e.g. {"kind":"hmrc_manual","code":"VIT13500","version":"2026-03-04"}
    ancestry: list[str]              # heading/section chain
    source_anchor: str               # URL fragment / page+para locator into the original
    # --- content ---
    text: str                        # enriched text as embedded
    text_raw: str                    # verbatim source text (what citations quote)
    token_count: int
    # --- vectors & search ---
    embedding: Vector                # pgvector column
    fts: TSVector                    # Postgres FTS (generated column)
    embedding_model: str             # versioned — mixed-model corpora are forbidden per index
```

Filters are **first-class columns** (not JSONB) because metadata filtering is on every query path (doc 03) and must use btree indexes alongside HNSW.

## 4. Embedding strategy

- **Model:** Azure OpenAI `text-embedding-3-large` (3072-d, truncated to 1536-d via dimensions parameter — the measured quality delta at 1536 is marginal for our corpus size and halves index memory; recorded with benchmark numbers when R2 lands). One embedding model version per index generation.
- **What gets embedded:** the *enriched* text (ancestry-prefixed) — ancestry context measurably improves retrieval of terse legal fragments; the *raw* text is preserved separately for quoting.
- **Re-embedding policy:** model upgrades create a **new index generation** side-by-side; the eval suite (`research-qa`) runs against both; cutover only on non-regression — never re-embed in place (the AP-2 mindset: retrieval behaviour changes are versioned, evaluated deployments).
- **No fine-tuned embeddings at MVP:** premature — hybrid retrieval + reranking (doc 03) recovers most domain-vocabulary loss; revisit trigger: measured vocabulary-gap failures in eval error analysis (e.g. statutory synonyms missed by both BM25 and vectors).
- Query-time: queries embed with the same model; domain agents pass `tax_domain`/`jurisdiction` filters from run context so embedding never carries the burden of scoping.

## 5. Index build & operations

- HNSW index (pgvector) per generation, built concurrently, `m`/`ef_construction` tuned on the eval set (defaults 16/64 until measured); btree composite indexes on `(tenant_id, jurisdiction, tax_domain)` and validity dates; GIN on `fts`.
- Corpus scale envelope at MVP: ~10–20k chunks (R2) growing to low hundreds of thousands (R4) — comfortably inside pgvector's competence (ADR-002); the `Retriever` port keeps Azure AI Search as the pressure valve.
- Nightly index-health job: orphan chunks (doc end-dated but chunks live), embedding-version consistency, FTS/vector row parity — discrepancies alert P5.
