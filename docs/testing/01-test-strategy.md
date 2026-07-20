# 01 — Test Strategy

## 1. Principles

1. **Tests are the spec's enforcement arm.** Every phase's guarantees exist as executable checks; a guarantee without a test is a proposal (the invariant suite is the canon of this).
2. **The weakest sufficient evaluator** (from docs/ai/05 §6, generalised): property test > example test > judge > human — pick the cheapest that measures the property; spend humans only where judgement is the property.
3. **Determinism first:** seeded data, frozen clocks, pinned models, recorded fixtures — a red build must mean a real regression. Non-deterministic classes (live-model evals) run separately with trend gates, not per-commit pass/fail.
4. **Test data is synthetic, always.** No client/production data in any test tier, ever (also the GDPR answer). The seed generator (Phase 6 doc 07 §2) is the single source of realistic data; **fixtures are generated, versioned by generator seed + version, never hand-edited** — "fix the test data" means "fix the generator."
5. **One failure vocabulary:** every suite reports into the same PR-check + dashboard taxonomy (doc 04) so "is main healthy" is one look, not eight.

## 2. Ownership & entry/exit criteria

| Suite | Owner (role) | Entry (runs when) | Exit (green means) |
|---|---|---|---|
| Unit/component/contract | Feature author | Every PR | Behaviour + contracts hold |
| Invariant | Platform (change requires ADR review) | Every PR | Architecture holds |
| AI evals | Agent/prompt author + eval owner | Prompt/model/registry/pack PRs; full on staging | Quality thresholds hold (docs/ai/05 tables) |
| Security | Security owner (P5 hat at MVP) | PR + nightly | Attack classes contained |
| E2E | Product/QA hat | main → staging deploy | Journeys work end-to-end |
| Performance | Platform | Nightly smoke; evidence run per train | NFR-06 evidenced (doc 02) |
| Release readiness | Release driver | Train cut | Doc 04 checklist complete |

Solo-builder reality (portfolio): one person wears all hats — the value of the table is that *the hats are named*, which is exactly what scales it to a team (and what an interviewer probes).

## 3. Test environments

| Tier | Runs | Data |
|---|---|---|
| Local | unit/component/int on compose | `minimal` seed |
| CI ephemeral | PR suites incl. kind-cluster helm-validate | fixtures + `minimal` |
| Staging | E2E, full evals (live models), DAST, perf smoke, drills | `demo` + `multi` + `scale` seeds |
| Perf environment | **Prod-shaped, ephemeral** — Terraform-built for evidence runs, destroyed after (same modules, prod SKUs; cost-bounded by lifespan) | `scale` seed |

The ephemeral-prod-shaped choice is deliberate: perf numbers from under-sized staging are noise; a standing perf env is waste. IaC makes the third option cheap — build, measure, publish, destroy (~4h window per evidence run).

## 4. Test-data management

- Generator profiles (Phase 6 doc 07 §2) extended with `scale` (1M+ rows, statistically realistic distributions: amount log-normals per vendor class, seasonal posting patterns, weekend/period-end effects) so performance tests exercise *plausible* data skew, not uniform noise.
- Seeded-findings manifest (`FINDINGS.md`) is the cross-suite ground truth: detector targets (docs/ml/02 §6), E2E assertions, and demo script all reference the same planted facts — one truth, three consumers.
- Golden sets (agents/retrieval/security) live in `evals/` with owners + change control (docs/ai/05 §2); generator-produced fixtures live in `tests/fixtures/` regenerated in CI to prevent drift (a fixture that can't be regenerated is deleted).
- PII discipline in test data: generator emits realistic-but-fake identities from a synthetic namespace (no real NI-number ranges, checksum-valid but reserved VAT numbers) — synthetic data that *looks* real enough to exercise the PII pipeline is part of the design.

## 5. Coverage philosophy (restated once, applies everywhere)

Numeric gates: 85% core / 95% engine+persistence (Phase 6), zero-serious axe (Phase 7), threshold tables (AI/ML/retrieval). But the review question is always behavioural: *"what breaks if this line is wrong, and which test notices?"* — mutation testing (nightly) audits the answer for the code where being wrong is an incident.
