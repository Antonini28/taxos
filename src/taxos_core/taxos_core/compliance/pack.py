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
    )


def load_pack(name: str, version: str, root: Path | None = None) -> RulePack:
    """Load a published pack from disk. In deployment this reads from Blob with a
    signature check (Phase 2 doc 07 §4); the interface is identical."""
    path = (root or PACKS_ROOT) / name / version / "pack.yaml"
    if not path.exists():
        raise PackError(f"pack {name}@{version} not found at {path}")
    return parse_pack(path.read_text(encoding="utf-8"))
