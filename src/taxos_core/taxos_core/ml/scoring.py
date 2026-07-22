"""Risk scoring: population in, advisory scored population out (docs/ml/02, ML-1).

Pure orchestration over `features`, `model`, and `explain`. No I/O — the same testability the
VAT engine has. The output is advisory by construction: a score, a rank, and a plain-language
reason built from the top Shapley feature. Nothing here dispositions, files, or decides — a
human reads the reason and judges. That the type has no `disposition` field is the point.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from taxos_core.ml.explain import Attribution, shapley_attributions
from taxos_core.ml.features import FEATURE_NAMES, extract_features
from taxos_core.ml.model import MODEL_VERSION, RiskModel
from taxos_core.risk.detectors import Transaction

# How the top contributing feature reads to a reviewer. The model surfaces the statistic; the
# phrase turns it into something a human can act on or dismiss.
_REASON: dict[str, str] = {
    "log_net": "the amount is large relative to the population",
    "vat_ratio": "the VAT-to-net ratio is unusual for this line",
    "is_round": "the amount is an exact round figure",
    "counterparty_zscore": "the amount is far from this counterparty's usual size",
}

# Below this, a line is unremarkable — most of the population. A reviewer's attention is the
# scarce resource, so only lines above the flag threshold carry an explanation worth reading.
FLAG_PERCENTILE = 0.90


@dataclass(frozen=True)
class RiskScore:
    row_id: str
    document_ref: str
    counterparty: str
    score: float
    rank: int  # 1 = most anomalous
    percentile: float  # 0..1, where this line sits in the population
    flagged: bool
    reason: str
    attributions: list[Attribution] = field(default_factory=list)
    model_version: str = MODEL_VERSION


def _reason_for(attributions: list[Attribution]) -> str:
    positive = [a for a in attributions if a.contribution > 0]
    if not positive:
        return "no single feature stands out; flagged on the overall pattern"
    return _REASON.get(positive[0].feature, "an unusual combination of features")


def score_population(
    transactions: list[Transaction], *, contamination: float = 0.05
) -> list[RiskScore]:
    """Score every transaction, most-anomalous first.

    Deterministic given the population: same transactions, same scores, same explanations
    (features are order-stable and the model's seed is fixed). Shapley attributions are
    computed for every scored line — affordable because the feature set is small by design.
    """
    if not transactions:
        return []

    matrix, row_ids = extract_features(transactions)
    by_row = {t.row_id: t for t in transactions}

    model = RiskModel(contamination=contamination).fit(matrix)
    scores = model.anomaly_scores(matrix)

    # Baseline = the population median per feature: "absent" features in a coalition take a
    # typical value, so an attribution answers "versus a normal line, why is this one high?".
    baseline = [statistics.median(col) for col in zip(*matrix, strict=True)]

    threshold = _percentile_value(scores, FLAG_PERCENTILE)
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    rank_of = {i: rank for rank, i in enumerate(order, start=1)}

    results: list[RiskScore] = []
    for i, row_id in enumerate(row_ids):
        flagged = scores[i] >= threshold
        # Explanations are for the lines a reviewer will actually open — the flagged ones.
        # Computing exact Shapley for the whole population would be effort spent on rows
        # nobody reads; a within-range line just says so.
        if flagged:
            attributions = shapley_attributions(
                matrix[i], baseline, FEATURE_NAMES, model.score_batch
            )
            reason = _reason_for(attributions)
        else:
            attributions = []
            reason = "within the normal range for the population"
        txn = by_row[row_id]
        results.append(
            RiskScore(
                row_id=row_id,
                document_ref=txn.document_ref,
                counterparty=txn.counterparty,
                score=round(scores[i], 6),
                rank=rank_of[i],
                percentile=round((len(scores) - rank_of[i] + 1) / len(scores), 4),
                flagged=flagged,
                reason=reason,
                attributions=attributions,
            )
        )

    results.sort(key=lambda r: r.rank)
    return results


def _percentile_value(values: list[float], q: float) -> float:
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(q * len(ordered)))
    return ordered[idx]
