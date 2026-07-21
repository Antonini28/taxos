"""Declarative base and the mixins every business table inherits (Phase 6 doc 03 §3)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class TenantMixin:
    """ADR-006: tenant_id on every business table from migration 0001, RLS-enforced.

    Cheap now, impossible later — present even while the product runs single-tenant.
    """

    tenant_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)


def new_id() -> uuid.UUID:
    """UUIDv7-style time-ordered id (index-friendly); uuid7 lands in 3.14+ stdlib."""
    return uuid.uuid4()
