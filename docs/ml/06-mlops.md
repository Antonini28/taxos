# 06 — MLOps: Registry, Pipelines, Monitoring, Drift

## 1. Model registry (ADR-016)

**MLflow** (tracking + registry), self-hosted as a small internal service (Postgres backend — same instance, separate database; artifacts in Blob under `models/`, layout already reserved in Phase 2 doc 04 §5).

Registered per model version: training-data snapshot ref (batch ids + feature-view version + label-set hash), code commit, hyperparameters, seeds, dependency lockfile hash, full eval report (incl. slice metrics + baseline comparisons), calibration artifacts, explanation-template version, promotion history with approver identity. **Promotion is a governed workflow:** `None → Staging` automatic on CI-green training runs; `Staging → Production` requires the eval checklist + a human approval recorded in the platform's own approval machinery (models are subject to the same GP-1 discipline as returns — a model going live is a state change of record). Serving code loads by stage alias per (tenant, detector); rollback = stage flip (previous version retained), effective at next scan (no long-lived serving processes to drain — batch serving makes rollback trivial).

**Why MlFlow over Azure ML registry:** MLflow is portable (no cloud lock-in for the portfolio's local story), integrates with our existing Postgres/Blob, and its API is the de facto standard; Azure ML is the documented enterprise swap (its registry speaks MLflow protocol — the migration is configuration). Why not a hand-rolled registry table: experiment tracking, artifact lineage UI, and stage semantics are commodity — build only the governance layer (promotion approvals) that MLflow lacks, on top.

## 2. Training pipelines (pipelines-as-code)

Training runs are **Celery-orchestrated pipeline tasks** (same worker infrastructure, `ml` queue, KEDA-scaled) defined as code in the repo — not notebook artifacts. Standard stages: snapshot (materialise feature views + labels with manifest) → validate data (schema, leakage checks: future-dated features, label contamination) → train (seeded) → evaluate (golden sets + temporal holdout + baselines + slices) → calibrate → register. Notebooks exist for exploration and are treated as documentation; nothing serves from a notebook. Scheduled retrains (per period-close for IF populations; volume/drift-triggered for supervised) create registry candidates — never auto-promote (the human gate is the point). No Kubeflow/Azure ML pipelines/Airflow at this scale: one more orchestrator is one more failure domain, and Celery already gives retries, routing, and observability; the pipeline-stage contract keeps a future lift-and-shift mechanical (trigger recorded: multi-hour GPU training jobs or DAG complexity beyond linear stages).

## 3. Model monitoring

Extends the doc 09 observability estate (metrics named there land on the *AI Model Monitoring* dashboard, which is also the admin UI page of the same name):

| Signal | Cadence | Alert |
|---|---|---|
| Score distribution vs training baseline (PSI per feature & score) | Per scan | PSI > 0.2 warn / > 0.3 ticket |
| Input drift (KS per feature; category novelty rate — new vendors/codes unseen in training) | Per scan | Sustained breach → retrain ticket |
| Precision proxy: disposition confirm-rate on model-flagged items (rolling) | Weekly | Drop >20% from promotion baseline |
| Calibration (ECE on realised dispositions) | Monthly | ECE > 0.1 |
| Alert-budget health: queue depth vs disposition throughput | Weekly | Backlog growth (ML-5 breach — the model is over-alerting for capacity) |
| Explanation quality chip rate (doc 05 §4) | Monthly | Trend review |
| Forecast MASE/coverage vs actuals | Per period-close | Doc 04 §3 |

## 4. Drift detection & response (FR-505)

Drift monitoring is a scheduled worker job (`model_drift_check`, already in the Phase 2 schedule table) writing `model_drift_report` rows consumed by the dashboard + alerting. **Response is a runbook, not an automation:** drift alert → analyst reviews aggregate-SHAP shift (doc 05 §3: *which features* moved) → classify: data-quality regression upstream (fix ingestion, don't retrain on corruption — the drift monitor is also a data-quality tripwire), genuine population shift (retrain ticket), or seasonal pattern (annotate + threshold review). Auto-retrain-on-drift is deliberately rejected: with disposition labels arriving slowly, an auto-retrained model can learn a data-quality bug faithfully and silently; every retrain passes the full promotion gate. Label drift (disposition-mix shift) is monitored separately — it usually signals *process* change (new reviewer, new policy) and gets a human conversation, not a model change.

## 5. Per-tenant model estate management

The registry is tenant-dimensional: (tenant, detector/model, population) → staged versions. Platform-level dashboard (P5) shows the estate grid: rung status (doc 01 §2), versions, last retrain, drift state, disposition volumes toward supervised-activation gates. Tenant onboarding starts every detector at Rung 0/1 automatically (rules + population stats need no history); the estate report makes "where is ML actually active" a queryable fact rather than tribal knowledge — which is precisely what a Big Four platform team must be able to answer per client.
