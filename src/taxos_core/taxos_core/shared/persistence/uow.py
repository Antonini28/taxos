"""The Audited Unit of Work — THE mutation path (Phase 6 doc 03 §2; ADR-003/009).

One service call = one UoW = one transaction containing:
    business mutations + hash-chained audit event(s) + outbox event(s)

`commit()` here is the only `session.commit()` in the codebase. Attempting to commit
without recording an audit draft raises — an unaudited mutation cannot reach the database.
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from taxos_core.audit.hashing import GENESIS_HASH, audit_payload, chain_hash
from taxos_core.audit.models import AUDIT_SERIALIZER_VERSION, AuditEvent
from taxos_core.shared.events.models import OutboxEvent


class UnauditedMutationError(RuntimeError):
    """Raised when a UoW commits without an audit record. This is a bug, loudly."""


@dataclass(frozen=True)
class Actor:
    """Who acted: a human, or an agent (with its run id for traceability)."""

    ref: str

    @staticmethod
    def user(email: str) -> "Actor":
        return Actor(ref=f"user:{email}")

    @staticmethod
    def agent(name: str, run_id: uuid.UUID) -> "Actor":
        return Actor(ref=f"agent:{name}:run:{run_id}")

    @staticmethod
    def system(component: str) -> "Actor":
        return Actor(ref=f"system:{component}")


@dataclass
class AuditDraft:
    action: str
    subject_type: str
    subject_id: str
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None


@dataclass
class DomainEvent:
    type: str
    payload: dict[str, Any]
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)


class AuditedUnitOfWork:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, actor: Actor) -> None:
        self._s = session
        self._tenant_id = tenant_id
        self._actor = actor
        self._audits: list[AuditDraft] = []
        self._events: list[DomainEvent] = []

    def record(
        self,
        action: str,
        subject_type: str,
        subject_id: str,
        *,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> None:
        self._audits.append(AuditDraft(action, subject_type, subject_id, before, after))

    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Buffered — nothing reaches the bus before the transaction commits (outbox, ADR-003)."""
        self._events.append(DomainEvent(type=event_type, payload=payload))

    async def _chain_tip(self) -> str:
        """Per-tenant chain tip under a transaction-scoped advisory lock.

        Why an advisory lock rather than `SELECT ... FOR UPDATE` on the tip row: the
        app role has no UPDATE privilege on `audit_event` (append-only, migration 0002),
        and row locks require it. The advisory lock serialises writers per tenant —
        which is the actual requirement — without granting a privilege that would
        weaken the immutability guarantee. Contention is scoped to one tenant's chain
        (the headroom this costs is measured by the `chain-contention` perf suite).
        """
        await self._s.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:tenant, 0))"),
            {"tenant": str(self._tenant_id)},
        )
        stmt = (
            select(AuditEvent.event_hash)
            .where(AuditEvent.tenant_id == self._tenant_id)
            .order_by(AuditEvent.seq.desc())
            .limit(1)
        )
        result = await self._s.execute(stmt)
        return result.scalar_one_or_none() or GENESIS_HASH

    async def commit(self) -> None:
        if not self._audits:
            raise UnauditedMutationError(
                "UoW.commit() called with no audit record — every state change must be attributable"
            )

        prev = await self._chain_tip()
        for draft in self._audits:
            payload = audit_payload(
                tenant_id=str(self._tenant_id),
                action=draft.action,
                subject_type=draft.subject_type,
                subject_id=draft.subject_id,
                actor=self._actor.ref,
                before=draft.before,
                after=draft.after,
                serializer_version=AUDIT_SERIALIZER_VERSION,
            )
            event_hash = chain_hash(prev, payload)
            self._s.add(
                AuditEvent(
                    tenant_id=self._tenant_id,
                    action=draft.action,
                    subject_type=draft.subject_type,
                    subject_id=draft.subject_id,
                    actor=self._actor.ref,
                    before=draft.before,
                    after=draft.after,
                    prev_hash=prev,
                    event_hash=event_hash,
                    serializer_version=AUDIT_SERIALIZER_VERSION,
                )
            )
            prev = event_hash

        for event in self._events:
            self._s.add(
                OutboxEvent(
                    event_id=event.event_id,
                    tenant_id=self._tenant_id,
                    type=event.type,
                    payload=event.payload,
                )
            )

        await self._s.commit()
