"""Knowledge: grounded tax research with citations (Phase 4, FR-401/402/403).

The corpus is global reference data (like `jurisdiction`) — shared, not tenant-scoped —
governed with source provenance and validity dates. Retrieval is deterministic (Postgres
full-text, no runtime LLM rewriting), so the same question yields the same passages every
time. Every answer cites its sources; when retrieval is weak the verdict is
INSUFFICIENT_SOURCES rather than a thin, unsupported reply — refusing to improvise is the
whole point.
"""
