# 04 — Quality Gates & Release Readiness

## 1. The consolidated gate map (single source; CI implements exactly this)

```
PR gate (must all pass; ~10 min budget):
  lint+types+guards (Phase 6 §2 table) · unit+component+contract · invariant suite
  · security unit set (authz matrix, tenancy) · frontend component+axe
  · affected AI evals (fixture mode) · helm-validate · coverage floors
  · bundle budget diff · openapi lint

main → staging gate (~30 min):
  integration suite · E2E J1–J8 · full eval suite (live models) · DAST baseline
  · visual regression · migration up/down verification

staging → prod gate:
  human approval (env protection) · staging soak green ≥ 24h (no SEV alerts)
  · error budget not exhausted (doc 09 burn policy)

nightly:
  mutation tests (engine+policies) · perf smoke (trend) · full DAST · dependency audit
  · drift plans · chain verification · eval trend report · flake report

per release train:
  perf evidence run (doc 02 §4) · internal pentest sprint + AI red-team (Phase 9 §4)
  · DR/rollback drill currency check · release-readiness checklist (§3)
```

Gate discipline: gates are added by PR to this document + CI together (the map *is* the config's spec); removing/weakening a gate requires the same review as an ADR change.

## 2. Quality dashboard (rendered in `/admin/system` + repo README badges)

| Tile | Source |
|---|---|
| Main health (all suites, latest) | CI |
| Coverage trend (core/engine) | CI artifacts |
| Eval headline metrics per agent (citation support, invariant violations, critic agreement) | eval runs |
| Model estate gates (drift, calibration, disposition confirm-rate) | docs/ml/06 monitors |
| Perf trend (nightly p95s vs SLO) | k6 → metrics |
| Flake rate per suite | CI analytics |
| Security posture (open findings by sev, MTTR) | Phase 9 §5 intake |
| Error budget burn | SLO monitors |

One place answers "would you ship main right now?" — and its screenshot is itself a portfolio artifact (quality engineering made visible).

## 3. Release-readiness checklist (per train; the ship/no-ship artifact)

```
□ All gate-map tiers green on the release SHA
□ Release BOM assembled (images, migrations, packs, prompts, model stages — Phase 8 §5)
□ Perf evidence report published for this train (or explicit waiver w/ reason)
□ Pentest/red-team findings ≥ high: closed or risk-accepted w/ owner + date
□ New ADRs merged for any architecture drift this train
□ Runbooks updated for new alerts/features; alert→runbook linkage verified
□ Migration contract-phase items from train N-1 executed or rescheduled
□ Rollback path verified this week (drill log)
□ Eval thresholds: no regression vs last train >2pp on headline metrics
□ Docs: user-facing changes reflected (Phase 11 set); demo script still passes (`just demo`)
□ DR rehearsal within currency window (quarterly)
□ Sign-off recorded (release driver; approver identity in the release annotation)
```

The checklist runs as a GitHub issue from a template per train — completed checklists accumulate as the audit trail of shipping discipline (SOC 2 CC8 evidence, for free).

## 4. Programme health metrics (quarterly self-review)

Escaped-defect count by suite-that-should-have-caught-it (the only metric that audits the *programme* rather than the code) · time-to-green on red main · flake trend · eval-fixture growth from production escapes (a growing suite from real escapes is health, not failure) · gate-runtime budgets (a 25-min PR gate is a process bug — parallelise or demote to nightly, decided deliberately).
