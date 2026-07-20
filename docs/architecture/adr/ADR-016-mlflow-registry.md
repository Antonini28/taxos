# ADR-016 — MLflow registry + Celery pipelines-as-code for the ML lifecycle

**Status:** Accepted · 2026-07-20 · Principles: AP-2 (reproducibility mindset), AP-5; FR-505, ML-4/ML-6 · Full design: `docs/ml/06-mlops.md`

## Context
FR-505 requires model registry, versioning, monitoring, and drift detection. The estate is per-tenant, batch-served, CPU-trained tree ensembles and statistical forecasters — no GPU fleets, no online serving. The MLOps market (Azure ML, Kubeflow, SageMaker-style stacks) is built for much heavier estates; the risk is buying an aircraft carrier to cross a river.

## Decision
1. **MLflow** (tracking + registry): Postgres backend (separate DB, same instance), artifacts in Blob (`models/` layout from Phase 2); registered versions carry full lineage — data-snapshot manifest, commit, seeds, lockfile hash, eval + calibration reports.
2. **Promotion is governed:** Staging automatic on CI-green; **Production requires human approval through the platform's own approval workflow** (a model going live is a state change of record — GP-1 applied to ML).
3. **Training pipelines are Celery pipeline tasks** (snapshot → validate/leak-check → train seeded → evaluate vs baselines+slices → calibrate → register) in the existing `ml` queue; notebooks never serve.
4. Per-tenant model dimensioning; batch serving loads by stage alias; rollback = stage flip.
5. Deferred with recorded triggers: dedicated feature store (feature count ×10 or >2 serving consumers), heavyweight orchestrator (GPU/multi-hour jobs or non-linear DAGs), Azure ML migration (registry protocol-compatible — configuration, not rewrite).

## Alternatives
- **Azure ML end-to-end** — capable and Azure-native, but locks the local/portfolio story to cloud resources, adds cost, and its value (compute orchestration, AutoML, endpoints) targets needs we don't have. Documented as the enterprise swap.
- **Kubeflow/Airflow/Dagster for pipelines** — a second orchestrator to operate; Celery already provides retries/routing/observability for linear pipelines at our scale.
- **Hand-rolled registry tables** — underestimates commodity scope (artifact lineage, experiment UI, stage semantics); we build only the governance layer MLflow lacks.
- **No registry (models as versioned files)** — fails FR-505 and the audit posture; rejected without ceremony.

## Consequences
- (+) Full reproduce-any-model capability (ML-4); promotion approvals land in the same audit chain as everything else; portfolio runs fully locally.
- (+) One infrastructure estate (Postgres/Blob/Celery) — no new failure domains for ML.
- (−) MLflow server is one more internal service (small; container in the existing environment; auth behind the platform's SSO proxy).
- (−) Celery pipelines lack DAG visualisation → pipeline stages emit OTel spans; the trace view is the DAG view (doc 09 machinery reused).
