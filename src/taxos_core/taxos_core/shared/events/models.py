"""Outbox table — the dual-write problem solved (ADR-003).

A relay polls unpublished rows (FOR UPDATE SKIP LOCKED) and publishes to the bus.
Crash between publish and mark = republish; consumers dedupe on event_id.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from taxos_core.shared.persistence.base import Base


class OutboxEvent(Base):
    __tablename__ = "outbox_event"
    __table_args__ = (Index("ix_outbox_unpublished", "published_at", "seq"),)

    seq: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, unique=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
