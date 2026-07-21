"""US-301: the deterministic engine, tested as a pure function.

No database here by design — if these tests needed one, the engine would not be pure.
"""

from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from taxos_core.compliance.engine import (
    EngineTransaction,
    compute_vat_return,
    inputs_hash,
)
from taxos_core.compliance.pack import load_pack

PACK = load_pack("uk-vat", "1.0.0")


def txn(row_id, direction, code, net, vat="0.00"):
    return EngineTransaction(
        row_id=row_id,
        direction=direction,
        vat_code=code,
        net_amount=Decimal(net),
        vat_amount=Decimal(vat),
    )


# --- correctness -------------------------------------------------------------


def test_standard_rated_sale_populates_output_vat_and_net_sales():
    result = compute_vat_return([txn("r1", "AR", "S20", "1000.00", "200.00")], PACK)
    assert result.box("box_1") == Decimal("200.00")
    assert result.box("box_6") == Decimal("1000")
    assert result.box("box_4") == Decimal("0.00")


def test_standard_rated_purchase_populates_input_vat_and_net_purchases():
    result = compute_vat_return([txn("r1", "AP", "S20", "500.00", "100.00")], PACK)
    assert result.box("box_4") == Decimal("100.00")
    assert result.box("box_7") == Decimal("500")
    assert result.box("box_1") == Decimal("0.00")


def test_derived_boxes_follow_the_pack_formulas():
    result = compute_vat_return(
        [txn("r1", "AR", "S20", "1000.00", "200.00"), txn("r2", "AP", "S20", "500.00", "100.00")],
        PACK,
    )
    assert result.box("box_3") == result.box("box_1") + result.box("box_2")
    assert result.box("box_5") == abs(result.box("box_3") - result.box("box_4"))
    assert result.box("box_5") == Decimal("100.00")


def test_reverse_charge_produces_both_output_and_input_entries():
    """The pack's signature rule: the buyer self-accounts, so one purchase touches
    Box 1 and Box 4 with equal amounts — net cash effect nil, both entries required."""
    result = compute_vat_return([txn("r1", "AP", "RC20", "4000.00", "0.00")], PACK)
    assert result.box("box_1") == Decimal("800.00")  # self-accounted output tax
    assert result.box("box_4") == Decimal("800.00")  # recovered as input tax
    assert result.box("box_5") == Decimal("0.00")  # self-cancelling
    assert result.box("box_7") == Decimal("4000")


def test_exempt_supplies_reach_box_6_but_carry_no_input_tax():
    result = compute_vat_return([txn("r1", "AR", "E00", "2000.00", "0.00")], PACK)
    assert result.box("box_6") == Decimal("2000")
    assert result.box("box_1") == Decimal("0.00")


def test_outside_scope_contributes_to_no_box():
    result = compute_vat_return([txn("r1", "AR", "O00", "5000.00", "0.00")], PACK)
    assert all(bv.value == Decimal("0") for bv in result.boxes.values())
    assert result.contributions == []


def test_unknown_codes_are_reported_never_guessed():
    """A code the pack does not define means the pack or the data is wrong. The engine
    reports it for a human; it never invents a treatment."""
    result = compute_vat_return([txn("r1", "AR", "ZZ9", "100.00", "20.00")], PACK)
    assert result.unmapped_codes == ["ZZ9"]
    assert result.box("box_1") == Decimal("0.00")


# --- FR-205 reproducibility ---------------------------------------------------


def test_identical_inputs_produce_identical_result_hash():
    txns = [txn("r1", "AR", "S20", "1000.00", "200.00"), txn("r2", "AP", "R05", "200.00", "10.00")]
    first = compute_vat_return(txns, PACK)
    second = compute_vat_return(txns, PACK)
    assert first.result_hash == second.result_hash


def test_row_order_does_not_change_the_result():
    """Re-fetching rows in a different order must not present as a different computation."""
    a = txn("r1", "AR", "S20", "1000.00", "200.00")
    b = txn("r2", "AP", "S20", "500.00", "100.00")
    assert (
        compute_vat_return([a, b], PACK).result_hash == compute_vat_return([b, a], PACK).result_hash
    )
    assert inputs_hash([a, b], PACK) == inputs_hash([b, a], PACK)


def test_different_results_produce_different_hashes():
    a = compute_vat_return([txn("r1", "AR", "S20", "1000.00", "200.00")], PACK)
    b = compute_vat_return([txn("r1", "AR", "S20", "1000.00", "200.50")], PACK)
    assert a.result_hash != b.result_hash


def test_inputs_hash_and_result_hash_answer_different_questions():
    """A 1p change in net vanishes inside whole-pound Box 6, so the RESULT is legitimately
    identical — but the INPUTS were not. The two hashes exist precisely so an auditor can
    distinguish "same answer" from "same evidence"."""
    a = txn("r1", "AR", "S20", "1000.00", "200.00")
    b = txn("r1", "AR", "S20", "1000.01", "200.00")

    assert compute_vat_return([a], PACK).result_hash == compute_vat_return([b], PACK).result_hash
    assert inputs_hash([a], PACK) != inputs_hash([b], PACK)


@settings(max_examples=150, deadline=None)
@given(
    rows=st.lists(
        st.tuples(
            st.sampled_from(["AP", "AR"]),
            st.sampled_from(["S20", "R05", "Z00", "E00", "O00", "RC20"]),
            st.decimals(
                min_value=0, max_value=100_000, places=2, allow_nan=False, allow_infinity=False
            ),
        ),
        min_size=0,
        max_size=40,
    )
)
def test_property_engine_is_deterministic(rows):
    """Property: for ANY input set, two runs agree exactly (FR-205)."""
    txns = [
        EngineTransaction(
            row_id=f"r{i}",
            direction=direction,
            vat_code=code,
            net_amount=net,
            vat_amount=(net * PACK.codes[code].rate).quantize(Decimal("0.01")),
        )
        for i, (direction, code, net) in enumerate(rows)
    ]
    first = compute_vat_return(txns, PACK)
    second = compute_vat_return(txns, PACK)
    assert first.result_hash == second.result_hash
    assert {k: v.value for k, v in first.boxes.items()} == {
        k: v.value for k, v in second.boxes.items()
    }


@settings(max_examples=100, deadline=None)
@given(
    nets=st.lists(
        st.decimals(min_value=0, max_value=50_000, places=2, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=25,
    )
)
def test_property_contributions_sum_to_box_value(nets):
    """Property (US-202 core): a box equals the sum of its contributions, exactly."""
    txns = [
        EngineTransaction(
            row_id=f"r{i}",
            direction="AR",
            vat_code="S20",
            net_amount=net,
            vat_amount=(net * Decimal("0.20")).quantize(Decimal("0.01")),
        )
        for i, net in enumerate(nets)
    ]
    result = compute_vat_return(txns, PACK)
    contributed = sum((c.amount for c in result.contributions_for("box_1")), Decimal("0"))
    assert contributed.quantize(Decimal("0.01")) == result.box("box_1")


# --- purity / AP-2 -------------------------------------------------------------


def test_engine_uses_no_floats_anywhere_in_its_output():
    result = compute_vat_return(
        [txn("r1", "AR", "S20", "1000.00", "200.00"), txn("r2", "AP", "RC20", "333.33", "0.00")],
        PACK,
    )
    for box in result.boxes.values():
        assert isinstance(box.value, Decimal)
    for contribution in result.contributions:
        assert isinstance(contribution.amount, Decimal)


def test_engine_module_imports_no_io_or_llm_dependencies():
    """AP-2 made mechanical: the engine's import graph must stay clean."""
    import taxos_core.compliance.engine as engine_module

    source = engine_module.__file__
    with open(source, encoding="utf-8") as handle:
        text = handle.read()
    for forbidden in ("import requests", "import openai", "sqlalchemy", "open(", "datetime.now"):
        assert forbidden not in text, f"engine must not reference {forbidden}"


def test_every_contribution_carries_its_citation():
    """Every figure can show the authority behind its treatment."""
    result = compute_vat_return([txn("r1", "AP", "RC20", "4000.00", "0.00")], PACK)
    assert result.contributions
    assert all(c.citation_ref for c in result.contributions)
    assert any("VATDSAG" in c.citation_ref for c in result.contributions)


# --- pack integrity ------------------------------------------------------------


def test_pack_content_hash_is_stable_and_pinned_in_results():
    result = compute_vat_return([txn("r1", "AR", "S20", "100.00", "20.00")], PACK)
    assert result.pack_ref == "uk-vat@1.0.0"
    assert result.pack_content_hash == PACK.content_hash
    assert len(PACK.content_hash) == 64


def test_pack_rejects_mapping_to_unknown_box():
    from taxos_core.compliance.pack import PackError, parse_pack

    broken = """
pack: broken
version: 0.0.1
jurisdiction: UK
tax_type: VAT
codes:
  S20:
    label: Standard
    rate: "0.20"
    citation: { source: test, ref: TEST }
    ar: { output_vat: box_99 }
boxes:
  box_1: { label: "VAT due" }
"""
    with pytest.raises(PackError, match="unknown box"):
        parse_pack(broken)
