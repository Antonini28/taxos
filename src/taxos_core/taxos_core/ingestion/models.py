"""Ingestion models.

`batch` is immutable once validated (Phase 2 doc 04 §3): re-ingesting means a new
batch, so lineage from any computed figure back to its source rows stays intact.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from taxos_core.shared.persistence.base import Base, TenantMixin, TimestampMixin, new_id


class BatchStatus:
    RECEIVED = "RECEIVED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    VALIDATED_WITH_EXCEPTIONS = "VALIDATED_WITH_EXCEPTIONS"
    REJECTED = "REJECTED"


class Batch(Base, TenantMixin, TimestampMixin):
    __tablename__ = "batch"
    __table_args__ = (
        # US-201: the same file cannot be ingested twice for a period. Content hash,
        # not filename — renaming a file must not defeat the check.
        UniqueConstraint("tenant_id", "content_hash", "period_key", name="uq_batch_content_period"),
        Index("ix_batch_entity_period", "tenant_id", "entity_id", "period_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=new_id)
    entity_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("legal_entity.id"), nullable=False
    )
    period_key: Mapped[str] = mapped_column(String(20), nullable=False)  # "2026-Q2"
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)  # "AP", "AR", "GL"
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default=BatchStatus.RECEIVED)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accepted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quarantined_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    control_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TransactionRow(Base, TenantMixin):
    """A validated source transaction. `source_payload` preserves the row as supplied —
    evidence survives even as the typed schema evolves."""

    __tablename__ = "transaction_row"
    __table_args__ = (Index("ix_txn_batch", "tenant_id", "batch_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=new_id)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("batch.id"), nullable=False
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    document_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    document_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    counterparty: Mapped[str] = mapped_column(String(255), nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    vat_code: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    source_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class QuarantineRow(Base, TenantMixin):
    """A row that failed validation — kept with its reasons, never silently dropped."""

    __tablename__ = "quarantine_row"
    __table_args__ = (Index("ix_quarantine_batch", "tenant_id", "batch_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=new_id)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("batch.id"), nullable=False
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    failures: Mapped[list] = mapped_column(JSONB, nullable=False)  # [{rule, message, field}]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ValidationResult(Base, TenantMixin):
    """Per-batch validation report: rule-level counts for the UI and the Data agent."""

    __tablename__ = "validation_result"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("batch.id"), nullable=False
    )
    rule_id: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_rows: Mapped[list] = mapped_column(JSONB, nullable=False)
