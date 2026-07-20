# Phase 10 — Testing Programme

**Product:** Enterprise Agentic Tax Operating System (TaxOS)
**Status:** Complete — awaiting stakeholder review
**Inputs:** Phase 6 doc 06 (backend patterns + invariant suite), docs/ai/05 (AI evals), Phase 9 doc 04 (security suite), Phase 7 doc 05 §7 (frontend testing), NFR table (Phase 1)
**Last updated:** 2026-07-20

## What this phase adds

Phases 3–9 each specified their own verification (deliberately — tests were designed *with* the things they test). Phase 10 does four jobs: (1) consolidate them into one programme with ownership and gates, (2) specify **performance/load testing** in full (the one major class not yet designed), (3) define E2E + regression policy, (4) define release-readiness — the checklist that says "this train may ship."

## Test-class inventory (consolidated map)

| Class | Specified in | Gate |
|---|---|---|
| Unit / component / integration / contract | Phase 6 doc 06 | PR |
| **Invariant suite** (architecture-as-tests) | Phase 6 doc 06 §3 | PR — never skipped |
| AI evals (golden sets, judge, invariants) | docs/ai/05 | PR (affected agents) + staging full |
| ML model gates (baselines, slices, calibration) | docs/ml/01 §4, 06 | Model promotion |
| Retrieval quality | docs/knowledge/03 §5 | PR (corpus/retrieval changes) + nightly |
| Security suite (authz matrix, tenancy, injection PI-1..10) | Phase 9 doc 04 | PR + nightly DAST |
| Frontend (component+axe, MSW integration, visual) | Phase 7 doc 05 §7 | PR |
| E2E golden journeys | **This phase, doc 03** | main → staging |
| Performance / load / stress / soak | **This phase, doc 02** | Nightly smoke + per-train evidence run |
| DR / rollback / chaos drills | Phase 8 docs 03/05 | Scheduled (weekly/quarterly) |
| Mutation testing | Phase 6 doc 06 §4 | Nightly (engine + policies) |

## Document map

| # | Document | Covers |
|---|----------|--------|
| 01 | [Test Strategy](01-test-strategy.md) | Principles, ownership, test-data management, environments, entry/exit criteria |
| 02 | [Performance Testing](02-performance-testing.md) | Workload models, k6 suites, NFR-06 evidence plan, profiling, capacity statements |
| 03 | [E2E & Regression](03-e2e-and-regression.md) | Golden journeys, regression policy, visual regression, flake governance |
| 04 | [Quality Gates & Release Readiness](04-quality-gates-and-reporting.md) | The consolidated gate map, quality dashboard, ship checklist |
