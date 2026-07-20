# 05 — Citations, Source Validation & Hallucination Prevention

## 1. Citation model

A citation is a **typed, resolvable object**, not a footnote string:

```python
class Citation(BaseModel):
    citation_id: UUID
    kind: Literal["hmrc_manual","legislation","case","oecd","ifrs_pointer",
                  "internal_policy","corporate_doc","pack_rule","lineage"]
    ref: CitationRef            # e.g. {"code":"VIT13500","version":"2026-03-04"}
                                # or {"act":"VATA 1994","section":"26","sub":"3"}
    chunk_id: UUID | None       # corpus chunk quoted (None for pack_rule/lineage kinds)
    quote: str                  # verbatim text_raw excerpt actually relied on (≤ ~50 words)
    claim_span: str             # which sentence(s) of the answer this citation supports
    authority_rank: str
    valid_for: DateRange        # temporal validity at the as_of date of the question
    resolver_url: str           # deep link: corpus viewer anchor + outbound source link
```

Two non-corpus kinds close the loop with earlier phases: `pack_rule` (deterministic rule citations from ADR-005 — how R1 ships "cited AI" before RAG exists) and `lineage` (figures cite computation lineage — the VAT agent's variance claims resolve to transaction sets, not text). **Everything the platform asserts resolves to either a source passage or a data lineage** — one uniform citation UX for reviewers.

## 2. Citation generation pipeline

1. **Attributed generation:** the Research agent's structured output binds each `answer_block` to citation candidates *during* generation (schema: claim + citations[], not prose-then-attach) — attaching citations to already-written prose is where support drifts.
2. **Mechanical resolution:** every citation resolves (chunk exists, quote is a verbatim substring of `text_raw`, version matches as-of) — invariant layer, output rejected on failure (docs/ai/05 §1).
3. **Support verification:** entailment check that `quote` actually supports `claim_span` — Critic rubric criterion (R2) using the judge protocol; sampled human audit stream calibrates it.
4. **Derived-chunk resolution:** citations to `derived` chunks (thread/table summaries) auto-expand to constituent source chunks (doc 02 §2) — terminal citations always hit primary material.
5. **Rendering:** UI shows claim-level citation chips → side-panel with quote, ancestry, validity window, authority rank, and outbound link; evidence packs embed the same resolved payloads (a reviewer and an HMRC inspector see identical provenance).

## 3. Source validation

| Validation | When | Mechanism |
|---|---|---|
| Authenticity | Ingest | Trusted-source allow-list per adapter; fetch manifests (URL, TLS, hash, timestamp); B-class carries curator identity |
| Integrity | Continuous | Chunk `text_raw` hash vs stored doc hash; nightly index-health job (doc 02 §5) |
| Temporal validity | Query + render | As-of filtering (doc 03); render-time re-check warns if a cited version was superseded after the answer was produced (stale-citation banner on old work items) |
| Authority conflicts | Answer assembly | Rank-ordered presentation (A1 > A2 > A3 > A4 > B) — conflicts shown, never silently resolved (Research agent contract) |
| Licence | Render | `ifrs_pointer` kinds render as outbound references, never quoted beyond fair-use summary |

## 4. Hallucination prevention — defence in depth

The stack, inner to outer (each layer assumes the previous failed):

| # | Layer | Mechanism | Phase |
|---|---|---|---|
| 1 | **Don't ask the model for facts** | Deterministic engines compute; tools fetch; the LLM reasons over supplied context only (AP-2, ADR-005) | Built |
| 2 | **Grounded-only generation** | Research/domain prompts forbid uncited claims; training-memory answers prohibited by prompt contract ("your memory of tax law is presumed stale") | 03/04 agent specs |
| 3 | **Retrieval sufficiency gate** | CoverageDiagnostics → INSUFFICIENT_SOURCES path (FR-403): weak retrieval produces a refusal artifact, not a thin answer | doc 03 §3 |
| 4 | **Schema-enforced attribution** | Answer schemas require citations per claim block; figure fields are refs, not numerics | docs/ai/03 |
| 5 | **Mechanical invariants** | Citation resolvability, verbatim-quote check, figure-integrity parser — code, not judgement; runs on every output in prod | docs/ai/05 §1 |
| 6 | **Critic entailment review** | Quote-supports-claim verification + rubric faithfulness before human handoff | docs/ai/03 §3.6 |
| 7 | **Calibrated confidence + escalation** | Below-threshold confidence ⇒ ESCALATED, never a hedged answer (doc 02 §5 basis model) | docs/ai/02 |
| 8 | **Human gate** | Nothing becomes a position or filing without named-human approval (GP-1) | Phase 2 workflow |
| 9 | **Measurement** | ≥95% citation-support rate CI gate + online support-rate sampling + insufficiency-recall tracking (NFR-07) | docs/ai/05 |

Residual-risk statement (honest): layers 1–9 make *unsupported statements reaching a human unmarked* the failure mode to measure — target <1% escaping to the review stage, with every escape a logged incident feeding golden sets. Zero-hallucination claims are marketing; bounded, measured, evidenced-or-escalated is engineering.

## 5. Answer lifecycle & auditability

Every Research/agent answer persists as `knowledge_answer` (question, filters, index_generation, retrieval diagnostics, answer blocks, citations, model/prompt versions, confidence, consumer run) — reproducible to its exact configuration, referenced by work items that relied on it, included in evidence packs when a filed position cites research. The corpus's version chains guarantee those citations still resolve years later (nothing is deleted, doc 01 §2) — **answers age into evidence, not into dead links.**
