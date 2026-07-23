"""Rung 3: the supervised model learned from dispositions (docs/ml/03).

Pure tests. They pin the two disciplines that make this rung honest rather than a black box:
censored labels never become training negatives, and the model refuses to train on too few
labels instead of fitting a confident-looking model to noise.
"""

import numpy as np
from taxos_core.ml.supervised import (
    MIN_PER_CLASS,
    build_labels,
    train_or_refuse,
)


def _example_dispositions(n_per_class: int, *, censored: int = 0):
    """Synthetic (features, status, reason) triples where the label is genuinely predictable
    from the features — confirmed lines carry a high vat-gap and roundness, benign ones don't —
    so a model that learns anything beats chance."""
    rng = np.random.default_rng(7)
    out: list[tuple[list[float], str, str]] = []
    for _ in range(n_per_class):
        # confirmed: unusual ratio + round + far from counterparty
        out.append(([12.0, 0.05, 1.0, 4.0 + rng.normal(0, 0.3)], "CONFIRMED", "MISCLASSIFIED"))
    for _ in range(n_per_class):
        # true negative: normal ratio, not round, typical
        out.append(([9.0, 0.20, 0.0, 0.3 + rng.normal(0, 0.3)], "DISMISSED", "REVIEWED_ACCEPTABLE"))
    for _ in range(censored):
        out.append(([9.5, 0.20, 0.0, 0.4], "DISMISSED", "NO_TIME"))
    return out


def test_censored_dismissals_are_excluded_not_counted_as_negatives():
    """A 'no time' dismissal is a skipped review, not a benign label — it must not train the
    model to think unreviewed lines are safe."""
    dispositions = _example_dispositions(MIN_PER_CLASS, censored=5)
    examples, censored_excluded = build_labels(dispositions)

    assert censored_excluded == 5
    assert all(e.reason != "NO_TIME" for e in examples)
    assert sum(1 for e in examples if e.label == 1) == MIN_PER_CLASS
    assert sum(1 for e in examples if e.label == 0) == MIN_PER_CLASS


def test_model_refuses_to_train_on_too_few_labels():
    """The evidenced-refusal posture, like INSUFFICIENT_SOURCES: below the floor it returns a
    'not yet' with the counts, not a model."""
    examples, censored = build_labels(_example_dispositions(3, censored=2))
    report = train_or_refuse(examples, censored)

    assert report.sufficient is False
    assert report.model_auc is None
    assert report.n_confirmed == 3
    assert report.n_true_negative == 3
    assert report.n_censored_excluded == 2
    assert "INSUFFICIENT_LABELS" in report.note


def test_model_trains_and_reports_a_model_card_when_labels_suffice():
    """With enough labelled dispositions it trains, cross-validates against a baseline, and
    reports feature importance — the model card a promotion decision would read."""
    examples, censored = build_labels(_example_dispositions(20))
    report = train_or_refuse(examples, censored)

    assert report.sufficient is True
    assert report.model_auc is not None and report.model_auc >= 0.7  # learned the signal
    assert report.baseline_auc is not None
    assert report.beats_baseline is not None
    assert report.feature_importance
    assert {a.feature for a in report.feature_importance}  # named, per-feature


def test_a_confirmed_disposition_labels_positive_and_a_true_negative_labels_zero():
    examples, _ = build_labels(
        [
            ([9.0, 0.2, 0.0, 0.1], "CONFIRMED", "GENUINE_DUPLICATE"),
            ([9.0, 0.2, 0.0, 0.1], "DISMISSED", "RECURRING_CONTRACT"),
            ([9.0, 0.2, 0.0, 0.1], "OPEN", ""),  # undispositioned — not a label at all
        ]
    )
    labels = {e.reason: e.label for e in examples}
    assert labels == {"GENUINE_DUPLICATE": 1, "RECURRING_CONTRACT": 0}
