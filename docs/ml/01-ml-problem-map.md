# 01 — ML Problem Map

## 1. Use case → framing → label reality

| Use case (FR) | Framing | Labels: source & reality | Release | Doc |
|---|---|---|---|---|
| Duplicate invoice detection (FR-501) | Pairwise similarity + rules; **not** ML-first (duplicates are near-deterministic) | Not needed for core; dispositions refine fuzzy thresholds | R1 | 02 §2 |
| Transaction outlier detection (FR-501) | Unsupervised (Isolation Forest) over engineered features per (entity, tax-code) population | None at start → dispositions accumulate (FR-506) | R1 | 02 §3 |
| VAT-code misclassification (FR-501/502) | R1: rules (pack-derived legality checks) → R2: supervised multi-class "expected code" model; disagreement = flag | Historical coded transactions (abundant, noisy — the model learns the entity's own coding norm) | R1→R2 | 03 §3 |
| Transaction/case risk scoring (FR-502) | Supervised binary (disposition-confirmed issue vs dismissed) via GBM | **Cold at MVP** — activates when disposition count crosses threshold (≥500 dispositions, ≥50 positives per tenant) | R2 | 03 §2 |
| Vendor risk (FR-501) | Composite score: rules + aggregates + (R2) model-lift | Partial (fraud cases per vendor) | R1 basic → R2 | 02 §5 |
| Entity resolution / vendor dedupe (FR-503) | Probabilistic record linkage (blocking + Fellegi-Sunter/GBM over comparison vectors) | Weak supervision from exact-match pairs + curated hard negatives + reviewer merges | R2 | 03 §4 |
| Document classification (FR-105) | Supervised multi-class (doc type) — small model feeding the Document agent's routing | Curated + accumulating from human verification queue | R2 | 03 §5 |
| Invoice field extraction | LLM-based (Document agent, Phase 3/4) — *not* a classical ML build; noted for completeness | Verification queue corrections | R2 | docs/ai/04 §4.3 |
| Cash tax / VAT liability forecasting (FR-504) | Per-entity time series with regressors + hierarchy reconciliation | History is the label (24+ months needed; graceful "insufficient history" path) | R2 | 04 |
| Drift detection (FR-505) | Statistical monitors (PSI/KS), not a "model" | n/a | R2 | 06 §4 |

## 2. The cold-start ladder (ML-3 made operational)

```
Rung 0  Seeded synthetic (demo/dev): generator injects known duplicates, outliers,
        miscodings with ground truth → golden sets + demo credibility (US-801)
Rung 1  Rules + population statistics (R1 prod): pack-legality checks, robust z-scores,
        Benford-style digit tests, fuzzy duplicate matching — explainable, label-free
Rung 2  Unsupervised (R1): Isolation Forest per population; anomaly = "investigate",
        never "fraud" (vocabulary matters for reviewer trust and for defensibility)
Rung 3  Disposition harvest (R1 onward): every confirm/dismiss with reason code is a
        labelled example (FR-506 designed this in); reason codes give class granularity
Rung 4  Supervised lift (R2, gated on volume): GBM risk scorer ranks the queue;
        unsupervised + rules layers KEEP RUNNING (novel-pattern recall insurance —
        a supervised model only knows yesterday's fraud)
Rung 5  Feedback loop maturity (R3+): threshold tuning from alert-budget analytics,
        periodic retrain cadence, champion/challenger in registry
```

The ladder is per-tenant and per-detector — a tenant can be at Rung 4 on VAT-code checks and Rung 2 on payroll outliers simultaneously. The `anomaly` schema (detector id, model_version_id nullable) already supports mixed rungs.

## 3. Feature engineering foundation (shared)

Feature views are **SQL-defined, versioned views over the lineage-bearing schema** (`transaction_row`, vendor aggregates, calendar context) materialised per training snapshot and computed identically at scoring time (same SQL, same code path — the train/serve skew defence). A dedicated feature store (Feast et al.) is deliberately deferred: at our feature count (~100s) and two consumers, versioned SQL views + snapshot manifests deliver the guarantees without the infrastructure; revisit trigger recorded in ADR-016.

Core feature families: amount statistics (robust-scaled within entity × tax-code × period populations), temporal (day-of-week/month-end proximity, posting-vs-document lag), vendor aggregates (volume, code entropy, round-number ratio, new-vendor flags), tax-code context (rate consistency, reverse-charge markers from pack rules), document-linkage (has matched PO/GRN where data exists), and graph-lite counters (shared bank accounts/VAT numbers across vendors — feeding both anomaly features and entity resolution).

## 4. Evaluation & acceptance standards (apply to every model)

- **Primary metrics:** PR-AUC and precision@k at the tenant's alert budget (ML-5); recall reported at fixed precision floors. ROC-AUC reported but never the acceptance criterion (class imbalance makes it flattering).
- **Golden-set gates in CI** (shares the `anomaly-cases` fixtures with agent evals): seeded-issue recall ≥ targets in doc 02/03; no model promotes on aggregate metrics alone — slice analysis by entity, amount band, and tax code is part of the promotion checklist (a model that only works on one entity is a bug shaped like a metric).
- **Baseline discipline:** every supervised model must beat (a) the rules layer alone and (b) a logistic-regression baseline on the same features, by pre-registered margins — GBM complexity is earned, not assumed.
- **Calibration:** scores exposed to reviewers are calibrated (isotonic on holdout); ECE tracked in monitoring (a "90%" that's right 60% of the time destroys queue trust).
