"""The derived-box formula evaluator (AP-3): the arithmetic that makes a pack a pack.

These are pure — the evaluator has no I/O — and they pin two things: the grammar is exactly
as small as claimed (anything outside it is a load-time error), and a genuinely dangerous
input cannot execute. The engine trusts these guarantees, so they are asserted directly.
"""

from decimal import Decimal

import pytest
from taxos_core.compliance.formula import (
    FormulaError,
    eval_formula,
    formula_refs,
    validate_formula,
)


def test_evaluates_addition_and_subtraction_over_boxes():
    values = {"box_1": Decimal("200.00"), "box_2": Decimal("0.00"), "box_4": Decimal("100.00")}
    assert eval_formula("box_1 + box_2", values) == Decimal("200.00")
    assert eval_formula("abs(box_1 + box_2 - box_4)", values) == Decimal("100.00")


def test_multiplication_by_a_rate_literal_stays_decimal():
    """A Corporation Tax charge is a box times a rate; the literal must not introduce a float."""
    result = eval_formula("box_ttp * 0.19", {"box_ttp": Decimal("100000.00")})
    assert result == Decimal("19000.0000")
    assert isinstance(result, Decimal)


def test_unary_minus_and_nested_parentheses():
    values = {"a": Decimal("10"), "b": Decimal("3")}
    assert eval_formula("-(a - b) * 2", values) == Decimal("-14")


def test_formula_refs_lists_dependencies_but_not_the_abs_function():
    assert formula_refs("abs(box_3 - box_4)") == {"box_3", "box_4"}
    assert formula_refs("box_ttp * 0.19") == {"box_ttp"}


def test_reference_to_unknown_box_is_an_error():
    with pytest.raises(FormulaError, match="unknown box"):
        eval_formula("box_1 + missing", {"box_1": Decimal("1")})


@pytest.mark.parametrize(
    "bad",
    [
        "__import__('os').system('echo x')",  # no calls except abs
        "box_1 ** 2",  # exponentiation is not in the grammar
        "box_1 if box_2 else box_3",  # no conditionals
        "len(box_1)",  # no arbitrary functions
        "box_1 and box_2",  # no boolean operators
    ],
)
def test_grammar_rejects_anything_dangerous_or_out_of_scope(bad):
    with pytest.raises(FormulaError):
        validate_formula(bad)


def test_syntactically_invalid_formula_is_rejected():
    with pytest.raises(FormulaError, match="invalid formula"):
        validate_formula("box_1 +")
