# 04 — Forecasting (FR-504, R2)

## 1. Scope & consumers

Cash-tax and VAT-liability forecasts per entity and group-rollup, consumed by the Executive Dashboard (P4's "predictable cash tax") and the Reporting agent's board-pack commentary. Forecasts are **planning aids, never filed figures** — rendered with intervals, assumptions, and an `as_of`, and excluded from any computation path (AP-2 hygiene: forecasts and facts never share a table; `forecast_series` is its own store with no FK into computations).

## 2. Method (deliberately boring, defensibly so)

| Layer | Choice | Rationale |
|---|---|---|
| Per-series model | **Seasonal state-space / ETS + regressors** (statsmodels/statsforecast), per (entity, tax-type, period-frequency) | VAT liabilities are strongly seasonal, short-history (24–60 points), business-calendar-driven series — the regime where classical statistical methods reliably beat ML (M-competition evidence); they're also fast, stable, and interval-honest |
| Regressors | Known-future calendar effects (period lengths, quarter shape), optional tenant-supplied revenue plan | Improves turning-point behaviour without leaking unknowable futures |
| Baseline | Seasonal naïve (same quarter last year ± trend) | Every forecast must beat it on rolling-origin MASE or the model doesn't serve (baseline discipline again) |
| Intervals | Model-native prediction intervals, empirically calibrated on rolling-origin backtests (coverage tracking: an "80% interval" must cover ~80% — reported on the dashboard tooltip) | Uncalibrated intervals are decoration |
| Hierarchy | Bottom-up entity→group with reconciliation check vs direct group fit (MinT reconciliation if divergence material) | CFO sees consistent rollups |
| Insufficient history (<24 points) | Explicit `INSUFFICIENT_HISTORY` output — dashboard shows the gap, not a fabricated line | The forecasting sibling of INSUFFICIENT_SOURCES |

**Why not Prophet/N-BEATS/foundation time-series models:** short business series with strong known seasonality don't reward them; ETS-class models are transparent (components decompose into level/trend/season — explainable to a CFO), dependency-light, and their failure modes are visible. Gradient-boosted or neural forecasters enter only via champion/challenger with rolling-origin evidence (same gate as everything else). Recorded here as the standing answer to "why so simple": because the evaluation said so, and the machinery to change the answer exists.

## 3. Operations

Backtests are the eval suite: rolling-origin evaluation across all history at every retrain (per period-close), MASE/coverage gates before serving; forecast runs are registry-tracked (model config, history snapshot ref, regressor set) like any model (ML-4). Monitoring: forecast-vs-actual error posted each period-close to the model dashboard; sustained MASE degradation or coverage breach → retrain ticket + dashboard caveat banner. Scenario support (R3): tenant-adjustable regressor assumptions (revenue plan variants) rendered as labelled scenario bands — assumptions are visible inputs, never baked-in.
