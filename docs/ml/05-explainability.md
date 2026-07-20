# 05 — Explainability (FR-502; ML-2)

## 1. SHAP vs LIME (the brief's question, answered for production)

| | TreeSHAP (SHAP for tree ensembles) | LIME |
|---|---|---|
| Faithfulness | **Exact** Shapley values for trees — the attribution *is* the model's arithmetic | Local surrogate approximation — two runs can explain the same prediction differently |
| Stability | Deterministic | Sampling-based, unstable (a compliance reviewer showing HMRC two different explanations for one score is a credibility incident) |
| Cost | Fast for tree models (polynomial algorithm) | Per-explanation sampling cost |
| Fit to estate | Perfect: every supervised model is a tree ensemble by design (doc 03); Isolation Forest attributions also SHAP-computable | Model-agnostic (its one advantage — which we don't need, having chosen the estate for explainability) |

**Decision: TreeSHAP everywhere; LIME nowhere in production.** LIME appears once — in the model-development notebook toolkit as a sanity cross-check during feature engineering — and is never a stored or displayed artifact. Instability is disqualifying for evidence (ML-2); this is the standing answer to "why not LIME". KernelSHAP (model-agnostic, slow) is likewise reserved for offline analysis only. *Choosing model families for exact explainability, rather than bolting approximate explainers onto arbitrary models, is the architectural decision — the explainer choice then makes itself.*

## 2. Explanations as stored evidence (not on-demand recomputation)

SHAP payloads are computed **at scoring time** and stored on the anomaly/score row with `model_version_id` (schema from Phase 2, doc 04 §3): you cannot faithfully re-derive an explanation after the model moves, and evidence packs must show *what the reviewer saw when they decided*. Payload: top-k signed contributions (feature, value, contribution), base value, model version, feature-view version — bounded size (full vectors to Blob if ever needed for analysis).

## 3. Rendering — three audiences, one payload

| Audience | Rendering |
|---|---|
| Reviewer (anomaly detail UI) | Plain-language contribution list, house-templated per feature family: *"Amount is 4.2× this vendor's typical invoice (+0.31)"*, *"First transaction with this vendor (+0.22)"* — templates versioned with the feature views (a feature without a template fails the promotion checklist; unexplainable features don't ship) |
| Risk agent (SHAP translation) | Raw payload via `get_anomaly_explanation`; the agent's narrative must preserve direction and rank — mechanically checked (docs/ai/04 §4.4: 100% fidelity invariant) |
| Analyst (model monitoring) | Aggregate SHAP: global importance drift, per-slice contribution shifts — feeds drift interpretation (doc 06 §4: *why* the model drifted, not just that it did) |

Rules-layer and duplicate-detector explanations flow through the same UI contract (fired-rule trace / component-score breakdown mapped to the same contribution-list shape) — **the reviewer experience never depends on which detector class flagged the row**, which is what lets the detector stack evolve without retraining humans.

## 4. Explanation governance

- Explanations are versioned evidence: payload schema changes are migrations; templates change via PR with reviewer-facing changelog.
- The Critic/invariant layer treats explanation fields as citations — a narrative referencing a contribution that isn't in the payload fails figure-integrity (docs/ai/05 §1).
- Monitoring includes an **explanation quality signal**: reviewer feedback chip on the explanation itself ("this explanation helped / didn't") — a cheap label stream for template improvement and a leading indicator of feature-set staleness.
