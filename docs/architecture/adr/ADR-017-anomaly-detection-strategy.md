# ADR-017 — Anomaly detection: permanent rules layer + per-population Isolation Forest; autoencoder behind an evidence gate

**Status:** Accepted · 2026-07-20 · Principles: AP-2, AP-5; FR-501/502/506, ML-1/2/3/5 · Full design: `docs/ml/02-fraud-anomaly-detection.md`

## Context
FR-501 requires anomaly/fraud detection at MVP with zero labelled fraud history (ML-3 cold start), reviewer-grade explainability (ML-2), and reviewer-capacity-bounded alerting (ML-5). The brief lists Isolation Forest and AutoEncoder among candidate techniques.

## Decision
1. **Three permanent detector classes, all always running:** versioned rules layer (pack-legality, digit tests, velocity, thresholds — institutional knowledge as config), two-stage fuzzy duplicate detection (blocking + explainable pairwise scoring — deliberately not ML), and **Isolation Forest fit per (entity, tax-code family, direction) population** (min 5k rows; robust z-score fallback below).
2. Alert thresholds set by **per-tenant alert budget** (precision@k at reviewer capacity), decoupled from model scores; contamination never assumed.
3. Dispositions (reason-coded, FR-506) accumulate as labels; a supervised GBM ranking layer (doc 03 §2) **stacks on top** at Rung 4 — unsupervised + rules keep running as novel-pattern insurance.
4. **AutoEncoder is not built at MVP.** Adoption gate (either trigger, evidenced from disposition analysis): (a) interaction-shaped false negatives in ≥100k-row populations that IF's axis-parallel splits demonstrably miss; (b) sequential/temporal fraud patterns (structured splitting over time) requiring representation learning. If triggered, it enters as a champion/challenger candidate through the standard promotion gate.
5. Refit governance: per period-close, versioned per fit; ranking-stability check (Kendall-τ ≥ 0.9 on seeded fixtures) quarantines erratic refits before serving.

## Alternatives
- **Autoencoder from day one** — needs more data per population than many will have, heavier infra, calibration-sensitive thresholds, and reconstruction-error attributions that are weak evidence for reviewers (ML-2 fails); adopted only when evidence shows IF's ceiling.
- **One-class SVM / LOF** — distance-metric sensitivity on mixed-scale tabular features, poor scaling, no better explainability; dominated by IF for this data shape.
- **ML-based duplicate detection** — duplicates are near-deterministic; fuzzy rules are more accurate, fully explainable, and tunable per tenant without training data.
- **Supervised-only (skip unsupervised)** — impossible at cold start (no labels) and fragile after (learns only yesterday's fraud).
- **Global cross-entity models** — every large entity's normal is another's outlier; population design *is* the model design.

## Consequences
- (+) Day-one detection with zero labels, every flag explainable in reviewer language, alert volume matched to capacity.
- (+) The disposition loop turns operations into training data — the estate improves as a by-product of use (Rung ladder, doc 01 §2).
- (−) Per-population model count is large (hundreds) → mitigated: seconds-per-fit training, registry population-grid tracking (doc 06 §5).
- (−) IF misses interaction/sequence anomalies by construction → known ceiling, monitored via false-negative disposition analysis — which is exactly the evidence stream the autoencoder gate reads.
