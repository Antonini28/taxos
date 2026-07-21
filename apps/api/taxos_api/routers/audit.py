"""Audit trail endpoints (FR-702).

Read-only, and deliberately so: there is no endpoint here that writes, amends, or deletes
an audit event. The log is written by the unit of work as a side-effect of doing business,
never by anyone choosing to write to it.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from taxos_core.audit.models import AuditEvent
from taxos_core.audit.verify import verify_chain

from taxos_api.deps import Principal, current_principal, db_session

router = APIRouter(prefix="/audit", tags=["audit"])

PrincipalDep = Annotated[Principal, Depends(current_principal)]
SessionDep = Annotated[AsyncSession, Depends(db_session)]


class AuditEventOut(BaseModel):
    seq: int
    action: str
    subject_type: str
    subject_id: str
    actor: str
    before: dict | None
    after: dict | None
    event_hash: str
    prev_hash: str
    recorded_at: str


class ChainStatusOut(BaseModel):
    """The result of recomputing every link. `verified: false` is a security incident,
    not a display state — the UI treats it accordingly."""

    verified: bool
    events_checked: int
    head_hash: str | None
    broken_at_seq: int | None
    reason: str | None


@router.get("/events", response_model=list[AuditEventOut])
async def list_events(
    principal: PrincipalDep,
    session: SessionDep,
    actor: str | None = None,
    action: str | None = None,
    limit: int = Query(default=100, le=500),
) -> list[AuditEventOut]:
    stmt = select(AuditEvent).order_by(AuditEvent.seq.desc()).limit(limit)
    if actor:
        stmt = stmt.where(AuditEvent.actor.ilike(f"%{actor}%"))
    if action:
        stmt = stmt.where(AuditEvent.action.ilike(f"%{action}%"))

    events = list((await session.execute(stmt)).scalars().all())
    return [
        AuditEventOut(
            seq=e.seq,
            action=e.action,
            subject_type=e.subject_type,
            subject_id=e.subject_id,
            actor=e.actor,
            before=e.before,
            after=e.after,
            event_hash=e.event_hash,
            prev_hash=e.prev_hash,
            recorded_at=e.recorded_at.isoformat(),
        )
        for e in events
    ]


@router.get("/chain-status", response_model=ChainStatusOut)
async def chain_status(principal: PrincipalDep, session: SessionDep) -> ChainStatusOut:
    """Recompute the whole chain on demand.

    This is the endpoint that turns "we log things" into "we can prove the log": every
    link is rehashed from its stored payload, so a single altered row is located by
    sequence number rather than merely suspected.
    """
    result = await verify_chain(session, principal.tenant_id)
    return ChainStatusOut(
        verified=result.verified,
        events_checked=result.events_checked,
        head_hash=result.head_hash,
        broken_at_seq=result.broken_at_seq,
        reason=result.reason,
    )
