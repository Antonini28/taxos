"""Rung 3: a supervised model learned from reviewer dispositions (docs/ml/03, ADR-017).

The Isolation Forest (Rung 2) surfaces statistical outliers but never learns whether its flags
were *useful*. This rung closes the loop: a reviewer's disposition on an anomaly is a label —
confirmed means "worth flagging", a reason-coded dismissal means "benign" — and a gradient-
boosted classifier learns which patterns humans actually confirm.

Two disciplines make this honest rather than a black box:

  * Censored labels are excluded, not counted as negatives. A dismissal for lack of capacity
    ("NO_TIME") is not evidence a line was benign — the reviewer skipped it. Training on it as
    a negative teaches the model that "unreviewed = safe", exactly backwards (docs/ml/03 §2).

  * The model refuses to train until it has enough labels. With too few dispositions it does
    not produce a confident-looking model on noise; it returns INSUFFICIENT_LABELS with the
    counts, the same evidenced-refusal posture the knowledge layer takes for INSUFFICIENT_SOURCES.

Every trained model reports its cross-validated AUC against a logistic-regression baseline it
has to beat, and its global feature importance as mean |Shapley| — the same exact attribution
the rest of the estate uses, here over the classifier's predicted probability.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable
from dataclasses import dataclass, field

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score

from taxos_core.ml.explain import Attribution, shapley_attributions
from taxos_core.ml.features import FEATURE_NAMES

# sklearn's HistGradientBoosting is the zero-extra-dependency GBM; LightGBM is the documented
# production swap (ADR-016), the same pattern as ACA-over-AKS — a portable default, a named upgrade.
SUPERVISED_MODEL_VERSION = "gbm-1.0.0"

# Labels needed per class before the model will train. A floor, not a target: below it, any AUC
# is noise. Production sets this higher; the principle — refuse rather than pretend — is the point.
MIN_PER_CLASS = 8

_SEED = 20260722

# Dismiss reasons that are NOT evidence of benignity. Kept in sync with the reason taxonomy in
# risk.models, where each carries "(true negative)" or "(censored, ...)" in its description.
CENSORED_DISMISS_REASONS = frozenset({"NO_TIME"})


@dataclass(frozen=True)
class LabeledExample:
    features: list[float]
    label: int  # 1 = reviewer confirmed the flag; 0 = confirmed benign (a true negative)
    reason: str


@dataclass
class SupervisedReport:
    sufficient: bool
    n_confirmed: int
    n_true_negative: int
    n_censored_excluded: int
    min_per_class: int = MIN_PER_CLASS
    model_version: str = SUPERVISED_MODEL_VERSION
    note: str = ""
    # Populated only when sufficient — the model card.
    model_auc: float | None = None
    baseline_auc: float | None = None
    beats_baseline: bool | None = None
    feature_importance: list[Attribution] = field(default_factory=list)


def build_labels(
    dispositions: Iterable[tuple[list[float], str, str]],
) -> tuple[list[LabeledExample], int]:
    """Turn (features, status, reason) triples into labelled examples, excluding censored
    dismissals. Returns (examples, n_censored_excluded)."""
    examples: list[LabeledExample] = []
    censored = 0
    for features, status, reason in dispositions:
        if status == "CONFIRMED":
            examples.append(LabeledExample(features, 1, reason))
        elif status == "DISMISSED":
            if reason in CENSORED_DISMISS_REASONS:
                censored += 1  # skipped, not benign — never a training negative
            else:
                examples.append(LabeledExample(features, 0, reason))
    return examples, censored


def train_or_refuse(examples: list[LabeledExample], censored_excluded: int = 0) -> SupervisedReport:
    """Train a GBM on the labelled examples, or return an evidenced refusal if there are too
    few of either class to learn anything a reviewer could trust."""
    n_pos = sum(1 for e in examples if e.label == 1)
    n_neg = sum(1 for e in examples if e.label == 0)

    if n_pos < MIN_PER_CLASS or n_neg < MIN_PER_CLASS:
        return SupervisedReport(
            sufficient=False,
            n_confirmed=n_pos,
            n_true_negative=n_neg,
            n_censored_excluded=censored_excluded,
            note=(
                f"INSUFFICIENT_LABELS: training needs {MIN_PER_CLASS} of each class; there are "
                f"{n_pos} confirmed and {n_neg} true-negative disposition(s). "
                f"{censored_excluded} censored dismissal(s) were excluded rather than counted "
                "as negatives. The model declines to train on too few labels — an evidenced "
                "'not yet', not a confident model fitted to noise."
            ),
        )

    x = np.array([e.features for e in examples], dtype=float)
    y = np.array([e.label for e in examples], dtype=int)
    n_splits = min(5, n_pos, n_neg)
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=_SEED)

    # Configured for the small-label regime this rung lives in: no early-stopping holdout
    # (which on tiny data stops at a constant model), shallow trees, small leaves.
    model = HistGradientBoostingClassifier(
        random_state=_SEED, early_stopping=False, max_depth=3, min_samples_leaf=5
    )
    baseline = LogisticRegression(max_iter=1000)
    model_auc = float(cross_val_score(model, x, y, cv=cv, scoring="roc_auc").mean())
    baseline_auc = float(cross_val_score(baseline, x, y, cv=cv, scoring="roc_auc").mean())

    model.fit(x, y)
    importance = _global_importance(model, x)

    return SupervisedReport(
        sufficient=True,
        n_confirmed=n_pos,
        n_true_negative=n_neg,
        n_censored_excluded=censored_excluded,
        model_auc=round(model_auc, 3),
        baseline_auc=round(baseline_auc, 3),
        beats_baseline=model_auc >= baseline_auc,
        feature_importance=importance,
        note=(
            f"Trained on {n_pos + n_neg} labelled dispositions. Cross-validated ROC-AUC "
            f"{model_auc:.3f} vs a logistic-regression baseline at {baseline_auc:.3f}."
        ),
    )


def _global_importance(model: HistGradientBoostingClassifier, x: np.ndarray) -> list[Attribution]:
    """Mean |Shapley| per feature over the training set, using the classifier's predicted
    probability — the same exact attribution the rest of the estate uses, aggregated to a
    global picture of what the model relies on."""
    baseline = [statistics.median(col) for col in zip(*x.tolist(), strict=True)]

    def batch_proba(vectors: list[list[float]]) -> list[float]:
        return [float(p) for p in model.predict_proba(np.array(vectors, dtype=float))[:, 1]]

    totals = np.zeros(len(FEATURE_NAMES))
    sample = x.tolist()[:: max(1, len(x) // 30)]  # cap cost; the feature set is tiny regardless
    for row in sample:
        for attribution in shapley_attributions(row, baseline, FEATURE_NAMES, batch_proba):
            totals[FEATURE_NAMES.index(attribution.feature)] += abs(attribution.contribution)
    means = totals / len(sample)

    importance = [
        Attribution(feature=name, value=0.0, contribution=float(means[i]))
        for i, name in enumerate(FEATURE_NAMES)
    ]
    importance.sort(key=lambda a: a.contribution, reverse=True)
    return importance
