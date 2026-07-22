"""A deterministic synthetic benchmark for the risk model (docs/ml/06).

The demo population is a handful of rows — enough to show the screen, too few to say the
model *works*. So performance is measured against a synthetic population with known injected
anomalies: because we know which lines are planted, we can state precision honestly rather
than assert it. Generation is seeded, so the benchmark — and any number quoted from it — is
reproducible.

This is synthetic on purpose and labelled as such; it never enters the application. It exists
so a claim like "recovers most planted anomalies in the top decile" is a measurement, not a
hope — the same standard the rest of the platform holds itself to.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import numpy as np

from taxos_core.risk.detectors import Transaction

_SEED = 20260722


@dataclass(frozen=True)
class Benchmark:
    transactions: list[Transaction]
    planted: set[str]  # row_ids of the injected anomalies


def make_benchmark(n: int = 400, n_anomalies: int = 20) -> Benchmark:
    """A population of normal AP lines with `n_anomalies` planted outliers of three kinds:
    mis-coded VAT, round-and-large amounts, and extreme values."""
    rng = np.random.default_rng(_SEED)
    counterparties = [f"Supplier {chr(65 + i)}" for i in range(12)]

    nets = rng.lognormal(mean=8.5, sigma=0.6, size=n)
    ratios = rng.normal(0.20, 0.008, size=n)

    planted_idx = set(rng.choice(n, size=n_anomalies, replace=False).tolist())
    transactions: list[Transaction] = []
    planted: set[str] = set()

    for i in range(n):
        net = float(nets[i])
        ratio = float(ratios[i])
        if i in planted_idx:
            kind = i % 3
            if kind == 0:  # mis-coded VAT: standard-rate document at a wrong ratio
                ratio = 0.05
            elif kind == 1:  # round and large
                net, ratio = 48_000.0, 0.0
            else:  # extreme value for the counterparty
                net = net * 12
        net_d = Decimal(f"{net:.2f}")
        vat_d = Decimal(f"{net * ratio:.2f}")
        row_id = f"synth-{i:04d}"
        transactions.append(
            Transaction(
                row_id=row_id,
                document_ref=f"AP-{i:04d}",
                counterparty=counterparties[i % len(counterparties)],
                net_amount=net_d,
                vat_amount=vat_d,
                vat_code="S20",
            )
        )
        if i in planted_idx:
            planted.add(row_id)

    return Benchmark(transactions=transactions, planted=planted)


def precision_at_k(scored_row_ids: list[str], planted: set[str], k: int) -> float:
    """Share of the top-k scored lines that were genuinely planted — the honest metric."""
    top = scored_row_ids[:k]
    return sum(1 for r in top if r in planted) / k if k else 0.0
