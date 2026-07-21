"""Chain verification — turns "we log things" into "we can prove the log" (ADR-009).

Runs as a scheduled integrity job, on evidence-pack export, and in the invariant tests.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taxos_core.audit.hashing import GENESIS_HASH, audit_payload, chain_hash
from taxos_core.audit.models import AuditEvent


@dataclass
class ChainVerificationResult:
    verified: bool
    events_checked: int
    head_hash: str | None
    broken_at_seq: int | None = None
    reason: str | None = None


async def verify_chain(session: AsyncSession, tenant_id: uuid.UUID) -> ChainVerificationResult:
    """Recompute every link; any mismatch localises the tamper to a sequence number."""
    stmt = (
        select(AuditEvent).where(AuditEvent.tenant_id == tenant_id).order_by(AuditEvent.seq.asc())
    )
    events = (await session.execute(stmt)).scalars().all()

    prev = GENESIS_HASH
    for event in events:
        if event.prev_hash != prev:
            return ChainVerificationResult(
                verified=False,
                events_checked=len(events),
                head_hash=None,
                broken_at_seq=event.seq,
                reason="prev_hash does not match preceding event_hash (row inserted or removed)",
            )
        payload = audit_payload(
            tenant_id=str(event.tenant_id),
            action=event.action,
            subject_type=event.subject_type,
            subject_id=event.subject_id,
            actor=event.actor,
            before=event.before,
            after=event.after,
            serializer_version=event.serializer_version,
        )
        expected = chain_hash(prev, payload)
        if expected != event.event_hash:
            return ChainVerificationResult(
                verified=False,
                events_checked=len(events),
                head_hash=None,
                broken_at_seq=event.seq,
                reason="event_hash does not match recomputed payload hash (row content altered)",
            )
        prev = event.event_hash

    return ChainVerificationResult(
        verified=True,
        events_checked=len(events),
        head_hash=None if not events else prev,
    )
