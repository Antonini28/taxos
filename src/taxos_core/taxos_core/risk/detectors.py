"""Anomaly detectors — pure functions over a transaction population.

Rung 1 of the cold-start ladder (docs/ml/01 §2): rules, not a model. Duplicates and
round-number patterns are near-deterministic, and a rule that explains itself in one
sentence beats a score a reviewer cannot interrogate. Each finding carries a plain-language
explanation and the contributing evidence, because the explanation *is* the product —
a flag a reviewer cannot understand is a flag they will learn to ignore.
"""

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class Transaction:
    """The detector's input shape — decoupled from the ORM so detectors are testable
    without a database, the same discipline the VAT engine follows."""

    row_id: str
    document_ref: str
    counterparty: str
    net_amount: Decimal
    vat_amount: Decimal
    vat_code: str


@dataclass(frozen=True)
class Finding:
    detector: str
    anomaly_type: str
    severity: str  # HIGH | MEDIUM | LOW
    row_id: str
    document_ref: str
    explanation: str
    evidence: dict = field(default_factory=dict)


# Detectors are versioned as a set so a stored anomaly records which rules judged it —
# the same reproducibility discipline as rule packs (ADR-005).
DETECTOR_VERSION = "1.0.0"

_ROUND_THRESHOLD = Decimal("10000")
_DUPLICATE_AMOUNT_TOLERANCE = Decimal("0.02")  # ±2% counts as a near-duplicate


def detect_duplicates(transactions: list[Transaction]) -> list[Finding]:
    """DUP-001: same counterparty, amount within tolerance, flagged as possible duplicate.

    The most common and most material AP anomaly — a genuinely duplicated payment. The
    match pair is named in the explanation so a reviewer can compare the two documents
    directly rather than hunt for the twin.
    """
    findings: list[Finding] = []
    by_counterparty: dict[str, list[Transaction]] = {}
    for txn in transactions:
        by_counterparty.setdefault(txn.counterparty, []).append(txn)

    for counterparty, group in by_counterparty.items():
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                if a.net_amount == 0:
                    continue
                delta = abs(a.net_amount - b.net_amount) / a.net_amount
                if delta <= _DUPLICATE_AMOUNT_TOLERANCE:
                    exact = a.net_amount == b.net_amount
                    findings.append(
                        Finding(
                            detector="DUP-001",
                            anomaly_type="POSSIBLE_DUPLICATE",
                            severity="HIGH" if exact else "MEDIUM",
                            row_id=b.row_id,
                            document_ref=b.document_ref,
                            explanation=(
                                f"{b.document_ref} matches {a.document_ref}: same "
                                f"counterparty ({counterparty}) and "
                                + (
                                    f"an identical net amount of £{b.net_amount:,.2f}."
                                    if exact
                                    else f"a net amount within 2% "
                                    f"(£{a.net_amount:,.2f} vs £{b.net_amount:,.2f})."
                                )
                            ),
                            evidence={
                                "match_document": a.document_ref,
                                "match_row_id": a.row_id,
                                "amount": str(b.net_amount),
                                "match_amount": str(a.net_amount),
                            },
                        )
                    )
    return findings


def detect_round_amounts(transactions: list[Transaction]) -> list[Finding]:
    """RND-001: exact round amounts above a threshold — worth a glance, commonly benign.

    Low severity by design: round numbers are weakly indicative, so this rule exists to
    surface for a quick look, not to accuse. Calibrating severity to the real strength of
    the signal is what keeps a queue trustworthy (docs/ml — alert-budget thinking).
    """
    findings: list[Finding] = []
    for txn in transactions:
        if txn.net_amount >= _ROUND_THRESHOLD and txn.net_amount % 1000 == 0:
            findings.append(
                Finding(
                    detector="RND-001",
                    anomaly_type="ROUND_AMOUNT",
                    severity="LOW",
                    row_id=txn.row_id,
                    document_ref=txn.document_ref,
                    explanation=(
                        f"{txn.document_ref} is an exact round amount "
                        f"(£{txn.net_amount:,.2f}) — worth a glance, commonly benign."
                    ),
                    evidence={"amount": str(txn.net_amount)},
                )
            )
    return findings


def detect_all(transactions: list[Transaction]) -> list[Finding]:
    """Run every detector. All run, always — an unsupervised layer stays in service even
    once a supervised layer is added, as novel-pattern insurance (docs/ml/02, Rung 4)."""
    return [*detect_duplicates(transactions), *detect_round_amounts(transactions)]
