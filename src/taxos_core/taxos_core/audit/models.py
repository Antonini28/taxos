"""The audit chain (ADR-009).

Append-only at three levels: DB grants (REVOKE UPDATE/DELETE), a trigger guard,
and the fact that only AuditedUnitOfWork writes here. `event_hash` chains each row
to its predecessor per tenant, so tampering breaks verification against WORM anchors.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from taxos_core.shared.persistence.base import Base

AUDIT_SERIALIZER_VERSION = "1.0"


class AuditEvent(Base):
    __tablename__ = "audit_event"
    __table_args__ = (
        Index("ix_audit_event_tenant_seq", "tenant_id", "seq"),
        Index("ix_audit_event_subject", "tenant_id", "subject_type", "subject_id"),
    )

    seq: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)

    action: Mapped[str] = mapped_column(String(100), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Actor is a human ("user:priya@corp.com") or an agent ("agent:vat:run:<id>")
    actor: Mapped[str] = mapped_column(String(255), nullable=False)

    before: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    serializer_version: Mapped[str] = mapped_column(String(10), nullable=False)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
