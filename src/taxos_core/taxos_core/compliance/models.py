"""Computation snapshots and lineage.

A computation is immutable evidence: it records what was computed, from which rows,
under which pack version, with which engine — so it can be re-verified years later
(FR-205). Lineage rows are the join that answers "why is Box 4 this number?" (US-202).
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from taxos_core.shared.persistence.base import Base, TenantMixin, TimestampMixin, new_id


class Computation(Base, TenantMixin, TimestampMixin):
    __tablename__ = "computation"
    __table_args__ = (
        # The same inputs under the same pack cannot be computed twice: accidental
        # duplicate computations are impossible rather than merely discouraged.
        UniqueConstraint("tenant_id", "inputs_hash", "pack_ref", name="uq_computation_inputs_pack"),
        Index("ix_computation_entity_period", "tenant_id", "entity_id", "period_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=new_id)
    entity_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("legal_entity.id"), nullable=False
    )
    period_key: Mapped[str] = mapped_column(String(20), nullable=False)
    tax_type: Mapped[str] = mapped_column(String(20), nullable=False)

    pack_ref: Mapped[str] = mapped_column(String(50), nullable=False)  # "uk-vat@1.0.0"
    pack_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(20), nullable=False)

    inputs_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)  # box values as strings
    batch_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    unmapped_codes: Mapped[list] = mapped_column(JSONB, nullable=False)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ComputationLine(Base, TenantMixin):
    """One box of one computation — the level a reviewer clicks."""

    __tablename__ = "computation_line"
    __table_args__ = (UniqueConstraint("computation_id", "box_id", name="uq_computation_line_box"),)

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=new_id)
    computation_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("computation.id"), nullable=False
    )
    box_id: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    derived: Mapped[bool] = mapped_column(nullable=False, default=False)


class ComputationLineSource(Base, TenantMixin):
    """The lineage association: which row contributed how much to which box.

    US-202's acceptance criterion — the sum of contributions must equal the box value
    exactly — is a query over this table, not a log to dig through.
    """

    __tablename__ = "computation_line_source"
    __table_args__ = (
        Index("ix_line_source_line", "tenant_id", "line_id"),
        Index("ix_line_source_row", "tenant_id", "row_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    line_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("computation_line.id"), nullable=False
    )
    row_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("transaction_row.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    vat_code: Mapped[str] = mapped_column(String(20), nullable=False)
    citation_ref: Mapped[str] = mapped_column(String(100), nullable=False)
