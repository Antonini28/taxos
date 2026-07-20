# 03 — Supervised Models

## 1. Gradient-boosting framework comparison (the brief's XGBoost / LightGBM / CatBoost question)

Evaluated for our reality: tabular, mixed numeric + high-cardinality categoricals (vendor, tax code), moderate data volumes (10⁵–10⁷ rows), CPU-only serving in workers, TreeSHAP explainability mandatory.

| Criterion | XGBoost | LightGBM | CatBoost |
|---|---|---|---|
| Categorical handling | Manual encoding needed | Native (int-coded), good | **Native ordered target-encoding — best in class, leak-resistant** |
| Small/medium-data robustness (overfit resistance) | Good with tuning | Leaf-wise growth overfits small data without care | **Strong defaults (ordered boosting)** |
| Training speed at our scale | Good | **Fastest** | Slower (acceptable at our sizes) |
| TreeSHAP support | ✔ | ✔ | ✔ (native) |
| Tuning burden | Highest | Medium | **Lowest (sane defaults)** |
| Ecosystem/maturity | Deepest | Deep | Deep enough |

**Decision:** **LightGBM as the default engine** (speed + maturity + native categoricals adequate with our feature prep), **CatBoost as the standing challenger** wherever high-cardinality categoricals dominate (vendor-heavy models: risk scoring, vendor lift) — the champion/challenger machinery (doc 06) makes this an empirical, per-model question rather than a religious one. XGBoost is not adopted: it wins nothing for us that the other two don't, and three frameworks in production is two too many. **Random Forest serves as the required strong baseline** (alongside logistic regression) in every training pipeline — if the GBM can't beat RF meaningfully, ship RF (simpler, more robust); this has decided real models before and the pipeline honours it (ML-4 baseline discipline, doc 01 §4).

## 2. Transaction/case risk scoring (FR-502, R2)

- **Target:** P(disposition = confirmed-issue | flagged) — trained on disposition outcomes (Rung 3→4), per tenant, activation gate ≥500 dispositions / ≥50 positives.
- **Features:** doc 01 §3 families + detector context (which detectors fired, rule ids, IF score) — the supervised layer learns *which anomalies matter*, explicitly stacking on the unsupervised layer rather than replacing it.
- **Label hygiene:** reason-coded dismissals are not all equal — `RECURRING_CONTRACT` is a true negative; `NOT_WORTH_TIME` is *censored*, not negative (excluded from training, tracked as a data-quality metric). This distinction is the difference between learning "what's benign" and learning "what reviewers are too busy for".
- **Validation:** temporal splits only (train past → validate future; random splits leak period effects); per-slice PR-AUC gates (doc 01 §4); calibration on temporal holdout.
- **Serving:** batch scoring in the `ml` queue on `AnomalyDetected`; scores + TreeSHAP payloads stored on the anomaly row (Phase 2 schema); queue rank = calibrated score × materiality band.

## 3. Tax-code (mis)classification (R2)

Multi-class "expected VAT code" model per tenant (LightGBM over transaction features + vendor history + line-text embeddings from the `fast` model route as dense features). Disagreement between predicted and booked code above confidence threshold ⇒ `POSSIBLE_MISCODING` anomaly citing the model's expectation with SHAP evidence. Honest framing in all UX: the model learns the entity's *own historical coding norm* — it detects *inconsistency*, not *illegality* (legality is the rules layer's job, from pack data). Noisy-label reality (historical bookings contain the very errors we hunt) is handled with confidence-threshold flagging only (no auto-suggestions below threshold) and periodic cleaning via confirmed-miscoding dispositions.

## 4. Entity resolution / vendor deduplication (FR-503, R2)

- **Approach:** probabilistic record linkage — blocking (normalised name tokens, VAT-number stems, bank-account, postcode) → comparison vectors (name Jaro-Winkler/token-set, address similarity, identifier exact/partial matches) → match scoring.
- **Engine decision:** evaluate **Splink** (MoJ open-source Fellegi-Sunter implementation — EM-trained, explainable match weights, built for exactly this, UK-government pedigree that plays well in this domain) against an in-house LightGBM pairwise classifier on weak-supervision labels (exact-match positives + blocked-random negatives + reviewer-merge decisions as gold). Selection by F1 on a labelled pair set at R2; Splink is the default hypothesis (per-comparison match weights are inherently reviewer-explainable — m/u probabilities read like evidence).
- **Governance:** resolution proposes `vendor_cluster` merges into a review queue — merges are human-confirmed (ML-1), reversible (cluster membership is versioned, never destructive), and feed duplicate detection (doc 02 §2) + vendor risk aggregation.

## 5. Document classification (R2)

Doc-type classifier feeding the Document agent's routing (docs/ai/04 §4.3): start with the `fast` LLM route zero-shot (it's already there, no training data needed), harvest the human verification queue into labels, then train a distilled classical model (linear over embeddings — cheap, fast, offline-capable) when volume justifies; promote only if it beats the zero-shot baseline on the labelled set at materially lower cost. This sequencing (LLM first, distil later) is the correct 2026 economics for low-volume classification tasks and is itself a talking point.

## 6. Deliberately not built

| Temptation | Why not |
|---|---|
| Deep tabular models (TabNet/FT-Transformer) | No evidence of lift over GBMs at our scale (consistent literature result); explainability and ops cost worse |
| One cross-tenant "fraud foundation model" | ML-6 governance boundary; tenants' fraud patterns are their data |
| Auto-remediation (auto-correcting codes) | ML-1; suggestions with evidence only |
| Real-time scoring API at MVP | No consumer needs <5-min latency (batch on validation events); a serving endpoint is R4-if-ever |
