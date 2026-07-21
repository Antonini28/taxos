"""Master data models (module-private per Phase 6 doc 02 §2)."""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from taxos_core.shared.persistence.base import Base, TenantMixin, TimestampMixin, new_id


class Tenant(Base, TimestampMixin):
    """The isolation boundary itself — not tenant-scoped (it IS the tenant)."""

    __tablename__ = "tenant"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)


class Jurisdiction(Base):
    """Global reference data (not tenant-scoped) — UK first, packs make it extensible (AP-3)."""

    __tablename__ = "jurisdiction"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)  # "UK"
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class LegalEntity(Base, TenantMixin, TimestampMixin):
    __tablename__ = "legal_entity"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_legal_entity_tenant_code"),)

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(50), nullable=False)  # "UK-01"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    jurisdiction_code: Mapped[str] = mapped_column(
        String(10), ForeignKey("jurisdiction.code"), nullable=False
    )


class TaxRegistration(Base, TenantMixin, TimestampMixin):
    """A registration is what creates obligations (FR-104 → FR-204)."""

    __tablename__ = "tax_registration"
    __table_args__ = (
        UniqueConstraint("tenant_id", "entity_id", "tax_type", name="uq_registration_entity_tax"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=new_id)
    entity_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("legal_entity.id"), nullable=False
    )
    tax_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "VAT", "CT"
    registration_number: Mapped[str] = mapped_column(String(50), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
