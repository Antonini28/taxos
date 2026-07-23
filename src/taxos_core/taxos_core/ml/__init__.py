"""Rung 2 of the risk ladder: an explainable, advisory statistical model (docs/ml).

The estate is deliberately layered on top of the rule detectors (Rung 1), never replacing
them. The model advises; a human decides; every score carries an exact Shapley explanation.
"""

from taxos_core.ml.explain import Attribution, shapley_attributions
from taxos_core.ml.features import FEATURE_NAMES, extract_features
from taxos_core.ml.model import MODEL_VERSION, RiskModel
from taxos_core.ml.scoring import RiskScore, score_population
from taxos_core.ml.supervised import (
    SUPERVISED_MODEL_VERSION,
    SupervisedReport,
    build_labels,
    train_or_refuse,
)

__all__ = [
    "FEATURE_NAMES",
    "MODEL_VERSION",
    "SUPERVISED_MODEL_VERSION",
    "Attribution",
    "RiskModel",
    "RiskScore",
    "SupervisedReport",
    "build_labels",
    "extract_features",
    "score_population",
    "shapley_attributions",
    "train_or_refuse",
]
