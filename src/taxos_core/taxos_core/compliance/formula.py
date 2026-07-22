"""Safe arithmetic for pack-declared derived boxes (AP-3).

A derived box's value is a formula over other boxes — "box_1 + box_2" for the VAT return's
Total VAT due, "profit + addbacks - deductions" for a Corporation Tax computation. Having
the engine *evaluate* these formulas, rather than hardcoding the arithmetic, is precisely
what lets a new tax type be authored as a pack instead of edited into the engine.

The grammar is deliberately tiny: box references, decimal literals, the four arithmetic
operators, unary minus, and abs(). Anything else is a pack error. Every formula is
validated when the pack loads (`validate_formula`), so evaluation at compute time can
trust its input and never has to defend against a malformed pack.

Literals are turned into Decimal via ``str()`` — a human-authored rate like 0.19 round-trips
exactly (str(0.19) == "0.19"), so no float ever reaches a tax figure.
"""

import ast
from collections.abc import Callable
from decimal import Decimal

_BINOPS: dict[type[ast.operator], Callable[[Decimal, Decimal], Decimal]] = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
}


class FormulaError(Exception):
    """A derived-box formula is malformed or references something that does not exist.
    Raised at pack load, never at compute time — a bad pack fails loudly and early."""


def _parse(formula: str) -> ast.expr:
    try:
        return ast.parse(formula, mode="eval").body
    except SyntaxError as exc:
        raise FormulaError(f"invalid formula {formula!r}: {exc.msg}") from exc


def formula_refs(formula: str) -> set[str]:
    """The box ids a formula depends on — used to order and validate derivations.

    `abs` is the one permitted function name, not a box reference, so it is excluded."""
    refs = {node.id for node in ast.walk(_parse(formula)) if isinstance(node, ast.Name)}
    refs.discard("abs")
    return refs


def validate_formula(formula: str) -> None:
    """Reject anything outside the permitted grammar, at load time."""
    _check(_parse(formula), formula)


def _check(node: ast.AST, formula: str) -> None:
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        _check(node.left, formula)
        _check(node.right, formula)
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        _check(node.operand, formula)
    elif _is_abs_call(node):
        _check(node.args[0], formula)  # type: ignore[attr-defined]
    elif isinstance(node, ast.Name):
        return
    elif isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return
    else:
        raise FormulaError(f"unsupported expression in formula {formula!r}")


def _is_abs_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "abs"
        and len(node.args) == 1
        and not node.keywords
    )


def eval_formula(formula: str, values: dict[str, Decimal]) -> Decimal:
    """Evaluate a validated formula over already-computed box values."""
    return _eval(_parse(formula), values, formula)


def _eval(node: ast.AST, values: dict[str, Decimal], formula: str) -> Decimal:
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        return _BINOPS[type(node.op)](
            _eval(node.left, values, formula), _eval(node.right, values, formula)
        )
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval(node.operand, values, formula)
    if _is_abs_call(node):
        return abs(_eval(node.args[0], values, formula))  # type: ignore[attr-defined]
    if isinstance(node, ast.Name):
        if node.id not in values:
            raise FormulaError(f"formula {formula!r} references unknown box {node.id!r}")
        return values[node.id]
    if isinstance(node, ast.Constant):
        return Decimal(str(node.value))
    raise FormulaError(f"unsupported expression in formula {formula!r}")
