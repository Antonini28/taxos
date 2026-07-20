# ADR-009 — Append-only audit log with hash chaining (in Postgres, anchored to WORM storage)

**Status:** Accepted · 2026-07-20 · Principles: AP-2, AP-4; NFR-04, GP-2

## Context
Evidence-by-default requires every state change to be attributable and the record tamper-evident — including against privileged insiders. Options range from plain log tables to full event sourcing to external ledger services.

## Decision
A single `audit_event` table: append-only (REVOKE UPDATE/DELETE from app roles + BEFORE UPDATE/DELETE trigger raising), written **in the same transaction** as the mutation it records, each row carrying `event_hash = SHA-256(prev_hash ‖ canonical_payload)`. A scheduled integrity job re-verifies the chain; chain heads are **anchored** (written to WORM Blob with timestamp) hourly, and evidence-pack export verifies the relevant slice. Actor is either a user (subject, session) or an agent (agent id, run id, plus the human approver where the action lands via an approved workflow step).

## Alternatives considered
1. **Plain audit table (no chain)** — a DBA/compromised admin can silently rewrite history; fails the "prove the log" bar that tax-authority and SAO scrutiny implies.
2. **Full event sourcing** — strictly stronger but re-platforms the whole domain (see ADR-002 alt 4); the chain gives tamper-evidence at ~2% of the complexity.
3. **Azure Confidential Ledger / QLDB-style managed ledger** — attractive managed tamper-proofing, but adds a second store on the critical write path (dual-write problem returns) and per-write cost. The chosen design keeps atomicity in one transaction and uses cheap WORM anchoring for the external-trust property. Revisit trigger: a client audit demands third-party-verifiable ledger custody.
4. **Write audit to append-only files/SIEM only** — loses transactional atomicity with the state change (an audited-but-rolled-back or changed-but-unaudited window), which is the exact property we need.

## Consequences
- (+) "Unaudited mutation cannot commit" is a provable invariant (tested by attempting mutations with audit disabled in integration tests).
- (+) Chain verification + anchoring converts audit from narrative to cryptographic evidence — a differentiator in doc 02's gap analysis.
- (−) Hash chaining serialises writes at the chain tip → mitigations: per-tenant chains (tip contention scoped to tenant), canonical serialisation kept cheap; measured in load tests before any further sharding.
- (−) Canonical JSON serialisation must be frozen (hash stability across versions) → serializer is versioned, version recorded per row.
