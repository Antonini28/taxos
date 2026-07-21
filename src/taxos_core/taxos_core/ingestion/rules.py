"""Validation rules — pure functions, no I/O, individually identifiable.

Each rule returns a failure carrying its own id and a human-readable message: the
quarantine queue must tell a preparer exactly what broke and where (US-201), not
"validation failed". Rules are versioned as a set so a batch records which set judged it.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

RULESET_VERSION = "1.0.0"

# Recognised UK VAT codes for the MVP slice. Real deployments source these from the
# jurisdiction content pack (ADR-005) — the shape here matches what the pack supplies.
VALID_VAT_CODES = {
    "S20": Decimal("0.20"),  # standard rate
    "R05": Decimal("0.05"),  # reduced rate
    "Z00": Decimal("0.00"),  # zero rated
    "E00": Decimal("0.00"),  # exempt
    "O00": Decimal("0.00"),  # outside scope
    "RC20": Decimal("0.20"),  # domestic reverse charge
}

VAT_TOLERANCE = Decimal("0.02")  # rounding tolerance on recomputed VAT


@dataclass(frozen=True)
class Failure:
    rule: str
    message: str
    field: str | None = None


@dataclass(frozen=True)
class ParsedRow:
    document_ref: str
    document_date: date
    counterparty: str
    net_amount: Decimal
    vat_amount: Decimal
    vat_code: str
    currency: str


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        return None


def validate_row(
    raw: dict[str, Any], *, period_start: date, period_end: date
) -> tuple[ParsedRow | None, list[Failure]]:
    """Parse and validate one row. Returns (parsed, failures); parsed is None if unusable.

    Money is parsed to Decimal here and stays Decimal from this point on — floats never
    touch a tax figure (ADR-005, lint-enforced in the compliance engine).
    """
    failures: list[Failure] = []

    # ING-001 required fields
    required = (
        "document_ref",
        "document_date",
        "counterparty",
        "net_amount",
        "vat_amount",
        "vat_code",
        "currency",
    )
    for field in required:
        if raw.get(field) in (None, ""):
            failures.append(Failure("ING-001", f"Required field '{field}' is missing", field))
    if failures:
        return None, failures

    # ING-002 date parseable and inside the declared period
    try:
        doc_date = date.fromisoformat(str(raw["document_date"]).strip()[:10])
    except ValueError:
        return None, [
            Failure(
                "ING-002", f"Unparseable document_date '{raw['document_date']}'", "document_date"
            )
        ]
    if not (period_start <= doc_date <= period_end):
        failures.append(
            Failure(
                "ING-003",
                f"document_date {doc_date} falls outside the batch period "
                f"({period_start} to {period_end})",
                "document_date",
            )
        )

    # ING-004 amounts numeric
    net = _decimal(raw["net_amount"])
    vat = _decimal(raw["vat_amount"])
    if net is None:
        failures.append(
            Failure("ING-004", f"net_amount '{raw['net_amount']}' is not a number", "net_amount")
        )
    if vat is None:
        failures.append(
            Failure("ING-004", f"vat_amount '{raw['vat_amount']}' is not a number", "vat_amount")
        )
    if net is None or vat is None:
        return None, failures

    # ING-005 known VAT code
    code = str(raw["vat_code"]).strip().upper()
    if code not in VALID_VAT_CODES:
        failures.append(
            Failure(
                "ING-005",
                f"Unknown VAT code '{code}' (expected one of {', '.join(sorted(VALID_VAT_CODES))})",
                "vat_code",
            )
        )
    else:
        # ING-006 VAT consistent with the code's rate (rounding tolerance applied).
        # Reverse-charge rows carry no VAT on the invoice — the charge is accounted
        # for by the buyer, so a zero here is correct rather than an error.
        expected = (net * VALID_VAT_CODES[code]).quantize(Decimal("0.01"))
        if code != "RC20" and abs(vat - expected) > VAT_TOLERANCE:
            failures.append(
                Failure(
                    "ING-006",
                    f"VAT {vat} inconsistent with code {code} on net {net} (expected ≈{expected})",
                    "vat_amount",
                )
            )
        if code == "RC20" and vat != Decimal("0"):
            failures.append(
                Failure(
                    "ING-006",
                    f"Reverse-charge row should carry zero invoice VAT, found {vat}",
                    "vat_amount",
                )
            )

    # ING-007 currency
    currency = str(raw["currency"]).strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        failures.append(Failure("ING-007", f"Invalid currency code '{currency}'", "currency"))

    if failures:
        return None, failures

    return (
        ParsedRow(
            document_ref=str(raw["document_ref"]).strip(),
            document_date=doc_date,
            counterparty=str(raw["counterparty"]).strip(),
            net_amount=net,
            vat_amount=vat,
            vat_code=code,
            currency=currency,
        ),
        [],
    )
