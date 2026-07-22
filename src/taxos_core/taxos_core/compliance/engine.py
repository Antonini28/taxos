"""The deterministic tax engine (AP-2, US-301).

Originally the VAT engine; now tax-type-neutral. What makes a return a *return* — its boxes,
their derivations, the codes that feed them, and the citations — is content in a rule pack
(see `pack.py`, `formula.py`), so a second tax type (UK Corporation Tax) computes here with
no change to this file. The engine supplies the reusable primitives: classify each row by
its pack code, accumulate signed contributions per box, then evaluate the pack's derived-box
formulas.

Properties this module guarantees, each covered by a test:

  * PURE — no I/O, no clock, no randomness, no database. Inputs in, result out.
  * DECIMAL ONLY — floats are never used for a tax figure. Rounding happens at the
    pack-defined points and nowhere else.
  * REPRODUCIBLE — identical (transactions, pack, params) always yields a byte-identical
    result, verified by an output hash and by property-based tests (FR-205).
  * TRACEABLE — every box value carries the contributions that produced it, so a
    reviewer can drill from a figure to its source rows (US-202).

The LLM never enters this file. Agents call the engine as a tool; they do not compute.
"""

import hashlib
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from taxos_core.audit.hashing import canonical_json
from taxos_core.compliance.formula import eval_formula
from taxos_core.compliance.pack import RulePack

ENGINE_VERSION = "1.0.0"

Direction = Literal["AP", "AR"]

# Contribution kinds that carry a NEGATIVE sign into their box. Everything else is +1 (see
# _sign_of). VAT has no negatives — every kind accumulates positively and the derived-box
# formula does any subtraction (Box 5 = |Box 3 − Box 4|). Corporation Tax is the same shape:
# add-backs and deductions both accumulate as positive totals, and the derived Taxable Total
# Profits formula subtracts the deductions. So this set is empty today, and the mechanism
# exists for a future pack that genuinely needs a signed contribution.
_NEGATIVE_KINDS: frozenset[str] = frozenset()


def _sign_of(kind: str) -> Decimal:
    return Decimal("-1") if kind in _NEGATIVE_KINDS else Decimal("1")


@dataclass(frozen=True)
class EngineTransaction:
    """The engine's input shape. Deliberately not the ORM model: the engine must be
    callable from tests, notebooks, and property generators without a database."""

    row_id: str
    direction: Direction
    vat_code: str
    net_amount: Decimal
    vat_amount: Decimal


@dataclass(frozen=True)
class Contribution:
    """One transaction's effect on one box — the atom of lineage (US-202)."""

    row_id: str
    box_id: str
    kind: str
    amount: Decimal
    vat_code: str
    citation_ref: str


@dataclass(frozen=True)
class BoxValue:
    box_id: str
    label: str
    value: Decimal
    derived: bool
    contribution_count: int


@dataclass(frozen=True)
class ComputationResult:
    pack_ref: str
    pack_content_hash: str
    engine_version: str
    boxes: dict[str, BoxValue]
    contributions: list[Contribution] = field(default_factory=list)
    unmapped_codes: list[str] = field(default_factory=list)

    @property
    def result_hash(self) -> str:
        """Stable fingerprint of the computation output.

        Two runs over identical inputs must produce the same hash — this is what
        FR-205 reproducibility is asserted against, and what an approval binds to.
        """
        payload = {
            "pack": self.pack_ref,
            "pack_hash": self.pack_content_hash,
            "engine": self.engine_version,
            "boxes": {k: str(v.value) for k, v in sorted(self.boxes.items())},
        }
        return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()

    def box(self, box_id: str) -> Decimal:
        return self.boxes[box_id].value

    def contributions_for(self, box_id: str) -> list[Contribution]:
        return [c for c in self.contributions if c.box_id == box_id]


def inputs_hash(transactions: list[EngineTransaction], pack: RulePack) -> str:
    """Fingerprint of what went in. Order-independent (sorted), so re-fetching rows in
    a different order does not present as a different computation."""
    rows = sorted(
        f"{t.row_id}|{t.direction}|{t.vat_code}|{t.net_amount}|{t.vat_amount}" for t in transactions
    )
    payload = {"pack": pack.ref, "pack_hash": pack.content_hash, "rows": rows}
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _quantize(value: Decimal, dp: int) -> Decimal:
    return value.quantize(Decimal(1).scaleb(-dp), rounding=ROUND_HALF_UP)


def compute_return(transactions: list[EngineTransaction], pack: RulePack) -> ComputationResult:
    """Compute a return from a rule pack. Pure: same inputs ⇒ same output, always.

    The pack decides everything tax-type-specific — boxes, codes, mappings, derivations —
    so this one function computes a UK VAT return or a UK Corporation Tax computation
    depending only on which pack it is handed.

    Unknown codes are REPORTED, never guessed and never silently ignored: a code the pack
    does not define means the pack or the data is wrong, and a human must decide which.
    """
    totals: dict[str, Decimal] = {box_id: Decimal("0") for box_id in pack.boxes}
    contributions: list[Contribution] = []
    unmapped: set[str] = set()

    for txn in sorted(transactions, key=lambda t: t.row_id):  # deterministic ordering
        rule = pack.codes.get(txn.vat_code)
        if rule is None:
            unmapped.add(txn.vat_code)
            continue

        for kind, box_id in sorted(rule.mapping_for(txn.direction).items()):
            if kind in ("output_vat", "input_vat"):
                amount = txn.vat_amount
            elif kind == "reverse_charge_output_vat":
                # The buyer self-accounts: output tax is computed from the net amount at
                # the pack's rate, because the supplier's invoice carries no VAT.
                amount = _quantize(txn.net_amount * rule.rate, pack.box_dp)
            else:  # net_sales / net_purchases
                amount = txn.net_amount

            if kind == "input_vat" and txn.vat_code == "RC20":
                # Reverse charge: the recoverable input tax equals the self-accounted
                # output tax, not the (zero) VAT on the invoice.
                amount = _quantize(txn.net_amount * rule.rate, pack.box_dp)

            signed = amount * _sign_of(kind)
            totals[box_id] += signed
            contributions.append(
                Contribution(
                    row_id=txn.row_id,
                    box_id=box_id,
                    kind=kind,
                    amount=signed,
                    vat_code=txn.vat_code,
                    citation_ref=rule.citation.ref,
                )
            )

    # Derived boxes: evaluate each pack-declared formula over the primary totals, in the
    # dependency order the pack computed at load. This is what keeps the arithmetic in the
    # pack rather than the engine — a new tax type derives its totals the same way, without
    # a line changing here (AP-3).
    for box_id in pack.derivation_order:
        formula = pack.boxes[box_id].formula
        assert formula is not None  # guaranteed by pack validation at load
        totals[box_id] = eval_formula(formula, totals)

    boxes: dict[str, BoxValue] = {}
    for box_id, definition in pack.boxes.items():
        value = _quantize(totals[box_id], pack.box_dp)
        if definition.whole_pounds:
            # HMRC boxes 6-9 are whole pounds; rounding is a pack decision, applied here.
            value = value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        boxes[box_id] = BoxValue(
            box_id=box_id,
            label=definition.label,
            value=value,
            derived=definition.derived,
            contribution_count=sum(1 for c in contributions if c.box_id == box_id),
        )

    return ComputationResult(
        pack_ref=pack.ref,
        pack_content_hash=pack.content_hash,
        engine_version=ENGINE_VERSION,
        boxes=boxes,
        contributions=contributions,
        unmapped_codes=sorted(unmapped),
    )


# The engine began life VAT-only; this alias keeps the VAT-specific call sites and tests
# reading naturally now that the function computes any pack.
compute_vat_return = compute_return
