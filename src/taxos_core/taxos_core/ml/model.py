"""The risk model — Rung 2 of the cold-start ladder (docs/ml/01 §2, ADR-017).

An Isolation Forest: unsupervised, so it needs no labels — which is the honest position at
cold start, when reviewer dispositions (the labels a supervised model would need) do not yet
exist. It surfaces statistical outliers in the transaction population; it does not know
"fraud", and it never decides. Its output is an advisory score and an explanation that a
human weighs (ML-1: advises, never decides).

Determinism is a first-class requirement, not a nicety: the random_state is fixed and the
input order is stabilised upstream (see `features.extract_features`), so the same population
yields the same scores every time. A score a reviewer cannot reproduce is one they cannot
act on.
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest

# Bumped when the model definition changes in a way that moves scores, so a stored score
# records which model produced it — the same versioning discipline as rule packs and
# detectors (ADR-005).
MODEL_VERSION = "isoforest-1.0.0"

_RANDOM_STATE = 20260722
_N_ESTIMATORS = 200


class RiskModel:
    """A thin, deterministic wrapper. Kept small on purpose: the governance is in how the
    score is *used* (advisory, human-gated, explained), not in the estimator itself."""

    def __init__(self, contamination: float = 0.05) -> None:
        self._forest = IsolationForest(
            n_estimators=_N_ESTIMATORS,
            contamination=contamination,
            random_state=_RANDOM_STATE,
        )
        self._fitted = False

    def fit(self, matrix: list[list[float]]) -> RiskModel:
        self._forest.fit(np.asarray(matrix, dtype=float))
        self._fitted = True
        return self

    def anomaly_scores(self, matrix: list[list[float]]) -> list[float]:
        """Higher means more anomalous. `score_samples` returns the opposite sign (higher =
        more normal), so we negate — a reviewer reads a big number as "look at this"."""
        if not self._fitted:
            raise RuntimeError("model must be fit before scoring")
        raw = self._forest.score_samples(np.asarray(matrix, dtype=float))
        return [float(-s) for s in raw]

    def score_one(self, row: list[float]) -> float:
        """Score a single feature row — used by the explainer to evaluate coalitions."""
        raw = self._forest.score_samples(np.asarray([row], dtype=float))
        return float(-raw[0])

    def score_batch(self, matrix: list[list[float]]) -> list[float]:
        """Score many rows in one pass. The explainer evaluates a whole row's coalitions this
        way, so exact Shapley costs one forest traversal batch per line, not one per subset."""
        raw = self._forest.score_samples(np.asarray(matrix, dtype=float))
        return [float(-s) for s in raw]
