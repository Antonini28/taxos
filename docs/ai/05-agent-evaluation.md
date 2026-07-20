# 05 — Agent Evaluation Framework

Evaluation is the release gate for AI behaviour the same way tests gate code (NFR-07). Three layers: **mechanical invariants** (cheap, absolute), **golden-set evals** (curated, CI-gated), **online quality monitoring** (production, trend-alerted). Prompt, model, rubric, and pack changes all trigger the same gates — a prompt edit without passing evals does not merge.

## 1. Mechanical invariants (run on every output, prod included)

Zero-tolerance checks executed in code (no LLM judging), enforced at the envelope boundary:

| Invariant | Applies to | Check |
|---|---|---|
| Figure integrity | All tax_domain, Reporting, Risk | Every numeric token in narrative fields must match a referenced snapshot/lineage/aggregate value (parser + ref resolver); violation ⇒ output rejected pre-Critic, step retried once, then escalated |
| Citation resolvability | All GROUNDED outputs | Every citation ref resolves to an existing passage/rule; dead refs reject the output |
| Schema validity | All | Pydantic-validated structured outputs (doc 02 §6) |
| Scope containment | All | No entity/tenant identifiers in output beyond the run's scope grant |
| Zero suppression | Fraud | Every pipeline anomaly id appears in the case report exactly once |
| No forbidden verbs | All | Output actions restricted to the agent's grant list (defence-in-depth vs the Tool Gateway) |

Invariant violations are telemetry events (doc 09 agent pillar) — a violation *rate* is a regression signal even when individual outputs are safely rejected.

## 2. Golden datasets

Curated, versioned in-repo (`evals/golden/`), synthetic-but-realistic (generator + hand-crafted edge cases; no client data ever):

| Set | Contents | Consumed by |
|---|---|---|
| `vat-scenarios` | ~50 entity-quarters: clean, reverse-charge, partial exemption, quarantine-heavy, seeded variances with known causes | VAT agent evals; engine property tests share fixtures |
| `data-readiness` | Complete/missing/short-volume batch configurations with labelled gaps | Data agent (gap recall ≥98%) |
| `anomaly-cases` | Seeded duplicates, misclassifications, legitimate-lookalikes with disposition ground truth | Fraud agent grouping/triage; detector PR-AUC separately (Phase 5) |
| `research-qa` | ~150 UK VAT/CT questions with gold citations + a subset the corpus deliberately cannot answer | Research agent (support ≥95%, insufficiency recall ≥95%) |
| `critic-defects` | Specialist outputs with planted defects (confabulated figures, unsupported claims, broken citations) + clean controls | Critic (catch ≥95%, false-reject <10%) |
| `plan-scenarios` | Instructions from clean to ambiguous to infeasible with expected plan shapes / expected escalations | Supervisor |
| `extraction-docs` | Labelled invoice/certificate corpus incl. degraded scans | Document agent (F1 ≥97%) |
| `reg-changes` (R3) | Historical change records with relevance labels per synthetic tenant profile | Regulatory Monitor |

Golden sets have owners and change control: additions via PR with rationale; removals require a recorded justification (deleting a failing case is the eval anti-pattern).

## 3. LLM-as-judge (where mechanics can't reach)

Faithfulness, register, and rubric adherence need semantic judgement. Protocol to keep the judge honest:
- Judge = `reasoning`-route model, **temperature 0, versioned prompt, pinned model version** — judge changes are themselves eval-gated (judge drift audit: re-run last accepted baseline, agreement ≥98% required before adopting a new judge version).
- Rubrics are per-agent YAML (criterion, description, severity weights) shared with the Critic — the offline judge and the online Critic apply the same standard.
- Every judge verdict samples a 5% human-audit stream (P3/P5 review in an internal tool) → judge-vs-human agreement (target κ ≥ 0.8) is itself a dashboard metric.
- Judge sees output + evidence refs, never the producing agent's identity/prompt (no sycophancy toward "known" agents).

## 4. CI/CD integration

```
PR (prompt/rubric/registry/agent-code change):
  invariant suite on golden outputs → full golden evals for affected agents
  → thresholds from the catalogue (docs 03/04) enforced as hard gates
  → cost report (eval spend per PR, cached fixtures for unchanged paths)

main → staging:
  full eval suite against staging (live models) → results to metrics (doc 09 §2)
  → regression vs last main run >2pp on any headline metric blocks promotion

nightly:
  full suite + judge-drift audit + threshold-trend report
```

Eval runs record: prompt versions, model versions, pack versions, golden-set version — every score is reproducible to its exact configuration (the AP-2 mindset applied to AI quality).

## 5. Online monitoring (production truth)

| Signal | Source | Alert condition |
|---|---|---|
| Invariant-violation rate per agent | envelope boundary | any sustained rise |
| Critic rejection rate per agent | run telemetry | spike (prompt/model regression) |
| Escalation precision | reviewer "correctly raised?" one-click feedback | falling trend |
| Human edit-distance on narratives | diff at approval time | rising trend |
| Disposition overturn rate | anomaly workflow | rising (Fraud case quality) |
| Confidence calibration | predicted vs realised (reviewer outcomes) | ECE drift |
| Cost per successful HANDOFF | CostRecords | budget-relative drift |
| Model-version change markers | deployment events | annotate all above dashboards |

Human feedback loops are deliberately cheap (one-click on escalations/cases at the point of work) — labelled production data accrues as a by-product of using the platform, feeding both golden-set growth and (Phase 5) model retraining.

## 6. What is *not* evaluated with LLM judges

Deterministic engines (bit-for-bit property tests — Phase 10), ML detectors (PR-AUC/precision@k — Phase 5), retrieval (labelled relevance sets — mechanical IR metrics). The rule: **use the weakest evaluator that can measure the property**; LLM judges are the evaluator of last resort, reserved for semantic faithfulness and register.
