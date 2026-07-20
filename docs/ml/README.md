# Phase 5 — Machine Learning

**Product:** Enterprise Agentic Tax Operating System (TaxOS)
**Status:** Complete — awaiting stakeholder review
**Inputs:** FR-501..506 (ML requirements), FR-207 (TP monitoring), Fraud/Risk agent specs (docs/ai/03–04), anomaly data model (docs/architecture/04 §3), NFR-07/08
**Last updated:** 2026-07-20

## Governing principles for ML in TaxOS

| # | Principle | Consequence |
|---|-----------|-------------|
| ML-1 | **ML advises; it never decides.** Scores create queue items and prioritisation; dispositions, adjustments, and filings are human acts (GP-1 extended to models) | No auto-blocking, no auto-writeoffs, no threshold that silently changes a filing |
| ML-2 | **Explainable by construction** | Model families chosen for faithful explanation (tree ensembles + TreeSHAP); explanation stored at scoring time with model version (FR-502; schema already in Phase 2) |
| ML-3 | **Label-realistic** | Fraud labels are scarce and delayed. The estate is designed around cold start: rules → unsupervised → dispositions-as-labels (FR-506) → supervised. No design step assumes labels we won't have |
| ML-4 | **Reproducible like the tax engine** | Versioned training datasets (snapshot refs), seeded runs, pinned dependencies, registry-tracked lineage: model → data → code commit (AP-2 mindset) |
| ML-5 | **Alert-budgeted** | Thresholds are set from reviewer capacity (precision@k at the daily alert budget), not from ROC vanity metrics — an ignored queue is a failed model |
| ML-6 | **Tenant-isolated learning** | Models train per-tenant by default; cross-tenant learning is an explicit enterprise-edition data-governance decision (same rule as episodic memory) |

## Document map

| # | Document | Covers |
|---|----------|--------|
| 01 | [ML Problem Map](01-ml-problem-map.md) | Use case → problem framing → label reality → release; the cold-start ladder |
| 02 | [Fraud & Anomaly Detection](02-fraud-anomaly-detection.md) | Duplicate detection, rules layer, Isolation Forest, autoencoder gate, vendor risk (→ ADR-017) |
| 03 | [Supervised Models](03-supervised-models.md) | Risk scoring (XGBoost/LightGBM/CatBoost comparison), tax-code/document/invoice classification, entity resolution |
| 04 | [Forecasting](04-forecasting.md) | Cash tax & VAT liability forecasting with intervals |
| 05 | [Explainability](05-explainability.md) | SHAP vs LIME, storage-at-scoring-time, UI & agent integration |
| 06 | [MLOps](06-mlops.md) | Registry, training pipelines, monitoring, drift detection, retraining governance (→ ADR-016) |
| — | [ADR-016](../architecture/adr/ADR-016-mlflow-registry.md) | MLflow registry + pipeline-as-code MLOps |
| — | [ADR-017](../architecture/adr/ADR-017-anomaly-detection-strategy.md) | Hybrid rules + Isolation Forest MVP; autoencoder behind evidence gate |
