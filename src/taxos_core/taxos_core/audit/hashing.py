"""Canonical serialisation + chain hashing.

The serialiser is VERSIONED and frozen: hash stability across releases is what makes
historical chains verifiable years later (ADR-009 consequences).
"""

import hashlib
import json
from typing import Any

GENESIS_HASH = "0" * 64


def canonical_json(payload: dict[str, Any]) -> str:
    """Deterministic JSON: sorted keys, no whitespace, UTF-8, stable number format."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )


def chain_hash(prev_hash: str, payload: dict[str, Any]) -> str:
    """event_hash = SHA-256(prev_hash ‖ canonical_payload)."""
    return hashlib.sha256((prev_hash + canonical_json(payload)).encode("utf-8")).hexdigest()


def audit_payload(
    *,
    tenant_id: str,
    action: str,
    subject_type: str,
    subject_id: str,
    actor: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    serializer_version: str,
) -> dict[str, Any]:
    """The exact fields covered by the hash. Adding a field is a serializer version bump."""
    return {
        "tenant_id": tenant_id,
        "action": action,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "actor": actor,
        "before": before,
        "after": after,
        "serializer_version": serializer_version,
    }
