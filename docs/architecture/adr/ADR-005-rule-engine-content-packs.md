# ADR-005 — Deterministic rule engine with versioned jurisdiction content packs

**Status:** Accepted · 2026-07-20 · Principles: AP-2, AP-3 (this ADR *implements* two fixed principles)

## Context
AP-2 forbids LLM arithmetic; AP-3 requires jurisdictions to be addable without core changes. The design question is *where tax logic lives*: hard-coded per jurisdiction, a general rules DSL, an external rules engine (Drools-style), or data-driven packs interpreted by a small deterministic engine.

## Decision
A **pure-function computation engine** (Python, `decimal` arithmetic, no I/O, property-tested for determinism) that interprets **signed, versioned, immutable content packs**: data artifacts (YAML/JSON in Blob, indexed in DB) containing rate tables, box mappings, classification rules, rounding rules, effective-date windows, filing calendars — each rule carrying a citation reference to its legal source (HMRC manual paragraph / legislation section). Pack schema versions independently of pack content. Computation records pin `(inputs_hash, pack_version)` forever (FR-205).

## Alternatives considered
1. **Hard-coded jurisdiction modules** — fastest for UK-only, but violates AP-3 (new jurisdiction = core release) and blurs the code/content boundary that tax content teams (the Big Four operating model: tax technical staff author content, engineers ship engines) depend on.
2. **Full rules DSL with authoring UI** — the ONESOURCE-style endgame, but a multi-year product in itself; premature. The pack schema *is* a narrow DSL; widen it capability-by-capability under schema versioning.
3. **External rules engine (Drools/OpenRules/Camunda DMN)** — JVM dependency in a Python estate, impedance mismatch with lineage capture (we need per-line contribution tracking, not just rule firing), and reproducibility depends on engine-version pinning we'd control less tightly.
4. **LLM-computed with verification** — categorically excluded by AP-2; noted only to record that "LLM + checker" still cannot yield the bit-for-bit reproducibility FR-205 demands.

## Consequences
- (+) Adding a jurisdiction = authoring + signing a pack (AP-3 satisfied mechanically); UK VAT pack is the reference implementation.
- (+) Every computed figure carries its rule citation → the UI can show "Box 4 includes X per VIT13500" (feeds FR-402-style trust).
- (+) Signature + hash pinning makes tax logic supply-chain-auditable (doc 07 §4).
- (−) Engine expressiveness limits what packs can express (e.g. partial-exemption special methods) → escape hatch: packs may reference *named engine capabilities* which are versioned code, still deterministic, still cited; capability additions are core releases (rare, reviewed).
- (−) Pack authoring has no UI at MVP (files + schema validation + review PRs) → acceptable; authoring workflow is an enterprise-edition feature.
