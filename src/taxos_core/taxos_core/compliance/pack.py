"""Rule-pack loading (ADR-005).

Packs are data, versioned and immutable. The loader validates structure and exposes a
typed view; it never mutates a pack, and the engine never reads files. Content hashing
lets a computation pin exactly which pack produced it — recomputation years later can
prove it used the same rules.
"""

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from taxos_core.compliance.formula import FormulaError, formula_refs, validate_formula

PACKS_ROOT = Path(__file__).resolve().parents[4] / "packs"


class PackError(Exception):
    """Structural problem with a pack — never silently tolerated: a malformed pack
    must fail loudly at load, not produce a subtly wrong return."""


@dataclass(frozen=True)
class Citation:
    source: str
    ref: str
    note: str


@dataclass(frozen=True)
class CodeRule:
    code: str
    label: str
    rate: Decimal
    citation: Citation
    ar: dict[str, str]  # contribution kind -> box id, for sales
    ap: dict[str, str]  # contribution kind -> box id, for purchases

    def mapping_for(self, direction: str) -> dict[str, str]:
        return self.ar if direction == "AR" else self.ap


@dataclass(frozen=True)
class BoxDef:
    id: str
    label: str
    derived: bool
    formula: str | None = None
    whole_pounds: bool = False


@dataclass(frozen=True)
class RulePack:
    name: str
    version: str
    jurisdiction: str
    tax_type: str
    schema_version: int
    rounding_mode: str
    box_dp: int
    codes: dict[str, CodeRule]
    boxes: dict[str, BoxDef]
    content_hash: str
    # Derived boxes in dependency order: a box whose formula builds on another derived box
    # comes after it, so the engine can evaluate them in a single left-to-right pass.
    derivation_order: tuple[str, ...] = ()

    @property
    def ref(self) -> str:
        return f"{self.name}@{self.version}"


def _require(data: dict[str, Any], key: str, context: str) -> Any:
    if key not in data:
        raise PackError(f"{context}: missing required key '{key}'")
    return data[key]


def parse_pack(raw: str) -> RulePack:
    """Parse and validate pack content. Hash is of the exact bytes supplied."""
    content_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise PackError("pack must be a mapping")

    codes: dict[str, CodeRule] = {}
    for code, spec in _require(data, "codes", "pack").items():
        citation_spec = _require(spec, "citation", f"code {code}")
        codes[code] = CodeRule(
            code=code,
            label=_require(spec, "label", f"code {code}"),
            rate=Decimal(str(_require(spec, "rate", f"code {code}"))),
            citation=Citation(
                source=_require(citation_spec, "source", f"code {code} citation"),
                ref=_require(citation_spec, "ref", f"code {code} citation"),
                note=citation_spec.get("note", ""),
            ),
            ar=dict(spec.get("ar") or {}),
            ap=dict(spec.get("ap") or {}),
        )

    boxes: dict[str, BoxDef] = {}
    for box_id, spec in _require(data, "boxes", "pack").items():
        boxes[box_id] = BoxDef(
            id=box_id,
            label=_require(spec, "label", f"box {box_id}"),
            derived=bool(spec.get("derived", False)),
            formula=spec.get("formula"),
            whole_pounds=bool(spec.get("whole_pounds", False)),
        )

    # Every box a code maps to must exist — a typo in a pack cannot silently drop
    # transactions from a return.
    for rule in codes.values():
        for direction_map in (rule.ar, rule.ap):
            for box_id in direction_map.values():
                if box_id not in boxes:
                    raise PackError(f"code {rule.code} maps to unknown box '{box_id}'")

    # Derived boxes are computed by the engine from their declared formulas, so the
    # arithmetic is content, not code (AP-3). Validate every formula at load: it must be
    # present, well-formed, and reference only boxes that exist — a malformed derivation
    # fails here, never as a subtly wrong return.
    derivation_order = _validate_derivations(boxes)

    rounding = data.get("rounding") or {}
    return RulePack(
        name=_require(data, "pack", "pack"),
        version=str(_require(data, "version", "pack")),
        jurisdiction=_require(data, "jurisdiction", "pack"),
        tax_type=_require(data, "tax_type", "pack"),
        schema_version=int(data.get("schema_version", 1)),
        rounding_mode=rounding.get("mode", "ROUND_HALF_UP"),
        box_dp=int(rounding.get("box_dp", 2)),
        codes=codes,
        boxes=boxes,
        content_hash=content_hash,
        derivation_order=derivation_order,
    )


def _validate_derivations(boxes: dict[str, BoxDef]) -> tuple[str, ...]:
    """Check every derived box's formula and return the derived boxes in dependency order.

    A derived box needs a formula that parses within the permitted grammar and references
    only known boxes. The ordering is a topological sort so a formula that builds on another
    derived box (VAT Box 5 depends on Box 3) is evaluated after it; a cycle is a pack error.
    """
    derived = {b.id for b in boxes.values() if b.derived}
    for box in boxes.values():
        if not box.derived:
            continue
        if box.formula is None:
            raise PackError(f"derived box '{box.id}' has no formula")
        try:
            validate_formula(box.formula)
        except FormulaError as exc:
            raise PackError(f"box '{box.id}': {exc}") from exc
        for ref in formula_refs(box.formula):
            if ref not in boxes:
                raise PackError(f"box '{box.id}' formula references unknown box '{ref}'")

    order: list[str] = []
    done: set[str] = set()
    visiting: set[str] = set()

    def visit(box_id: str) -> None:
        if box_id in done:
            return
        if box_id in visiting:
            raise PackError(f"cyclic derived-box formula involving '{box_id}'")
        visiting.add(box_id)
        for ref in formula_refs(boxes[box_id].formula or ""):
            if ref in derived:
                visit(ref)
        visiting.discard(box_id)
        done.add(box_id)
        order.append(box_id)

    for box_id in boxes:  # insertion order keeps the result deterministic
        if box_id in derived:
            visit(box_id)
    return tuple(order)


def load_pack(name: str, version: str, root: Path | None = None) -> RulePack:
    """Load a published pack from disk. In deployment this reads from Blob with a
    signature check (Phase 2 doc 07 §4); the interface is identical."""
    path = (root or PACKS_ROOT) / name / version / "pack.yaml"
    if not path.exists():
        raise PackError(f"pack {name}@{version} not found at {path}")
    return parse_pack(path.read_text(encoding="utf-8"))
