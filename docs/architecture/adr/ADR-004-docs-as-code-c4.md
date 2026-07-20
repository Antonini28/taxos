# ADR-004 — C4 model + Mermaid docs-as-code

**Status:** Accepted · 2026-07-20 · Principles: AP-4

## Context
Architecture documentation must be reviewable in PRs, versioned with the code it describes, and renderable where reviewers live (GitHub, IDEs) — or it rots.

## Decision
C4 model (Context → Container → Component; code level left to the code) expressed in **Mermaid** inside Markdown, stored in `docs/architecture/`, evolved via PRs. ADRs follow the Nygard format (Context/Decision/Alternatives/Consequences) with status lifecycle (Proposed → Accepted → Superseded-by-N).

## Alternatives considered
1. **Structurizr DSL** — best-in-class C4 tooling with model-once-render-many, but adds a build step and viewer dependency; GitHub can't render it inline. Revisit if diagram count × duplication becomes painful.
2. **Draw.io / Visio / Lucidchart** — binary/XML blobs that don't diff; review becomes "trust me it changed correctly". Rejected for anything load-bearing (acceptable for marketing-grade visuals in Phase 13).
3. **Confluence-style wiki** — divorces docs from code review and versioning; the enterprise graveyard of stale architecture.

## Consequences
- (+) Diagrams diff in PRs; docs changes ride the same review gate as code; stale-doc risk visibly reduced.
- (+) Zero licence cost; renders on GitHub, in IDEs, and in the future repo wiki (Phase 12).
- (−) Mermaid's layout control is limited for very dense diagrams → mitigated by C4 discipline (one level per diagram, subgraphs, several focused diagrams over one mural).
- (−) No single "model" source (each diagram hand-maintained) → acceptable at ~15 diagrams; Structurizr is the named escape hatch.
