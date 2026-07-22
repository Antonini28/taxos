"""Feature extraction for risk scoring — pure and deterministic (docs/ml/02).

The same discipline as the VAT engine: a pure function from the transaction population to a
feature matrix, no I/O, no clock, no randomness. Determinism matters more here than usual —
a risk score that a reviewer cannot reproduce is a risk score they cannot defend, so given
the same population these features are byte-identical every time.

The feature set is deliberately small and named. Two reasons: a reviewer can read what the
model looked at, and a small set makes *exact* Shapley attribution tractable (see `explain`).
Every feature is a quantity a tax reviewer already reasons about — size, VAT ratio, round
numbers, how a line compares to its counterparty's others — so an attribution to a feature
is an explanation, not a black box.
"""

import math
from statistics import mean, pstdev

from taxos_core.risk.detectors import Transaction

# Order is fixed and part of the contract: stored explanations reference features by name,
# and the model is trained on this column order.
FEATURE_NAMES: tuple[str, ...] = (
    "log_net",
    "vat_ratio",
    "is_round",
    "counterparty_zscore",
)

# Standard-rate VAT ratio; distance from it is a mis-coding signal, but we let the model
# learn that from vat_ratio rather than hardcoding a rule (that is Rung 1's job).
_ROUND_MIN = 10_000.0


def _is_round(net: float) -> float:
    return 1.0 if net >= _ROUND_MIN and net % 1000 == 0 else 0.0


def extract_features(transactions: list[Transaction]) -> tuple[list[list[float]], list[str]]:
    """Return (matrix, row_ids) with one feature row per transaction, in a stable order.

    Rows are sorted by row_id so re-fetching the population in a different order cannot
    change the matrix — the reproducibility guarantee the whole platform rests on.
    """
    ordered = sorted(transactions, key=lambda t: t.row_id)

    # counterparty_zscore needs each counterparty's own distribution, computed once.
    by_counterparty: dict[str, list[float]] = {}
    for txn in ordered:
        by_counterparty.setdefault(txn.counterparty, []).append(float(txn.net_amount))
    cp_stats: dict[str, tuple[float, float]] = {
        cp: (mean(nets), pstdev(nets)) for cp, nets in by_counterparty.items()
    }

    matrix: list[list[float]] = []
    row_ids: list[str] = []
    for txn in ordered:
        net = float(txn.net_amount)
        vat = float(txn.vat_amount)
        vat_ratio = vat / net if net > 0 else 0.0
        cp_mean, cp_std = cp_stats[txn.counterparty]
        # A line that sits far from its counterparty's usual size — a duplicate or an
        # outlier payment. Zero when the counterparty has one line or no spread.
        zscore = abs(net - cp_mean) / cp_std if cp_std > 0 else 0.0
        matrix.append(
            [
                math.log1p(net),
                vat_ratio,
                _is_round(net),
                zscore,
            ]
        )
        row_ids.append(txn.row_id)

    return matrix, row_ids
