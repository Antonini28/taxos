# 03 — E2E & Regression

## 1. Golden journeys (Playwright, against staging post-deploy; stub-LLM; `demo`+`multi` seeds)

The six from Phase 7 doc 05 §7, made precise with their assertion cores:

| # | Journey | Spine assertions (beyond "it works") |
|---|---|---|
| J1 | Login → executive dashboard → drill L1→L2→L3 | Filter context preserved across altitudes; every KPI reaches a record; `as_of` present |
| J2 | Upload batch → validation → quarantine review | Seeded control-total break caught; quarantined rows excluded downstream; duplicate re-upload rejected with link |
| J3 | Instruct agent → plan → escalation (missing payroll) → provide → resume → HANDOFF | Run parks (not fails); resumes from checkpoint (no recompute of done steps); ends AWAITING_HUMAN_REVIEW; trace complete |
| J4 | Review → lineage drill → approve; **and** SoD-denial branch (preparer attempts approve) | Box-4 lineage sums exactly; approve binds hash; SoD 403 + explanatory UI + audit row; post-approval lock |
| J5 | Anomaly queue → case → SHAP view → disposition | All 14 seeded duplicates present (FINDINGS.md cross-check); disposition stores reason; queue count decrements; label row exists |
| J6 | Document intake → review → correct low-confidence field → promote | Two-way overlay highlight; promote blocked until fields resolved; version history records correction |
| J7 *(added)* | Multi-tenant sweep: run J1+J5 as tenant-B user | Zero tenant-A artifacts visible anywhere (the E2E layer of TB7 — belt on top of the API-level suite) |
| J8 *(added)* | Auditor journey: audit log → filter by agent actor → export slice → chain-verify badge | Read-only UI (no mutating affordances in DOM, not just disabled); export completes; verification state shown |

E2Es assert through the UI but verify through the API where truth lives (e.g. J4 confirms the approval row via API call — screenshots can lie, contracts don't).

## 2. Regression policy

- **Every bug becomes a test first** (Phase 6 rule, programme-wide): the reproducing test is reviewed *failing* in the fix PR (reviewer checklist verifies the red→green history).
- Regression suites are the same suites — no separate "regression pack" to rot; a regression is a test that exists because reality found a gap, tagged `regression` with the issue link for archaeology.
- AI regressions: eval-set additions per docs/ai/05 §2 (escaped hallucinations, injection attempts, judge disagreements all become fixtures); model/prompt rollbacks (registry stage flip) are the hotfix path while the fixture lands.
- Flake governance (extends Phase 6 §4): quarantine within 24h, root-cause within sprint; flake rate per suite is a dashboard metric — >2% triggers a stability sprint-item; E2E waits are event-based only (`await expect(...)`, WS message hooks) — `sleep()` in a test is a review reject.

## 3. Visual regression

Playwright screenshots on the five flagship screens × light/dark × desktop/tablet, against committed baselines (perceptual diff, 0.1% threshold): catches token regressions, chart-wrapper changes, and dark-mode drift that axe can't see. Baseline updates are deliberate PR artifacts (a visual diff in review = a design decision, not a rubber stamp). Storybook composite states get snapshot coverage too — the design system's states (doc 01 §6 inventory) stay true as components evolve.

## 4. What E2E deliberately does not cover

Exhaustive permutations (the API/component layers own breadth — E2E owns *integration truth*, ~8 journeys, <15 min wall time); live-LLM behaviour (evals own it — E2E with live models would be flake theatre); load (doc 02); email delivery and real OIDC redirects (contract-tested at boundaries, verified manually per train via the release checklist's smoke items).
