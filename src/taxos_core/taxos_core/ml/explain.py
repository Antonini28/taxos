"""Exact Shapley attribution for a risk score (docs/ml/04, ADR-018).

Every score gets an explanation: how much each feature contributed to *this* transaction's
anomaly, as a Shapley value. The design commits to Shapley attribution because it is the one
method with axioms a reviewer (or an auditor) can rely on — efficiency (the parts sum to the
whole), symmetry, and a zero for a feature that changes nothing.

The usual objection to Shapley is cost: exact values need every coalition, which is
exponential. We sidestep it rather than approximate it. The feature set is small *by design*
(see `features.FEATURE_NAMES`), so the 2**k coalitions are cheaply enumerable — a handful of
features means exact Shapley values, not the sampled estimate a general-purpose library
returns. Explainability you cannot argue with beats explainability you have to caveat.

A feature that is "absent" from a coalition is set to the population baseline (its median),
so a contribution answers "how much did this value, versus a typical one, raise the score?"
"""

import itertools
import math
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Attribution:
    feature: str
    value: float
    contribution: float  # Shapley value: signed contribution to the anomaly score


def shapley_attributions(
    row: list[float],
    baseline: list[float],
    feature_names: tuple[str, ...],
    batch_score_fn: Callable[[list[list[float]]], list[float]],
) -> list[Attribution]:
    """Exact Shapley values for one row, by full coalition enumeration.

    Every coalition's masked vector (features in the coalition at their actual value, the rest
    at `baseline`) is scored in a *single* batch call, so exact Shapley costs one scoring pass
    per line rather than one per subset — what keeps the exact method affordable. Returned
    attributions sum to score(row) - score(baseline) exactly (the efficiency axiom), sorted by
    magnitude so the reason a line was flagged reads top-first.
    """
    n = len(feature_names)
    indices = list(range(n))

    # Enumerate every subset once, build its masked vector, and score them all together.
    subsets: list[frozenset[int]] = []
    vectors: list[list[float]] = []
    for size in range(n + 1):
        for combo in itertools.combinations(indices, size):
            s = frozenset(combo)
            subsets.append(s)
            vector = list(baseline)
            for j in s:
                vector[j] = row[j]
            vectors.append(vector)
    scores = batch_score_fn(vectors)
    value = dict(zip(subsets, scores, strict=True))

    phi = [0.0] * n
    for i in indices:
        others = [j for j in indices if j != i]
        for size in range(len(others) + 1):
            weight = math.factorial(size) * math.factorial(n - size - 1) / math.factorial(n)
            for combo in itertools.combinations(others, size):
                s = frozenset(combo)
                phi[i] += weight * (value[s | {i}] - value[s])

    attributions = [
        Attribution(feature=feature_names[i], value=row[i], contribution=phi[i]) for i in indices
    ]
    attributions.sort(key=lambda a: abs(a.contribution), reverse=True)
    return attributions
