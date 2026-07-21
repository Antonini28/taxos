"""Workflow models.

Approvals are append-only and bind to a content hash rather than to an id: approving
"computation X" means approving *the version of X you read*. If the inputs change, the
hash no longer matches and the approval is void — recorded as an event, not erased.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from taxos_core.shared.persistence.base import Base, TenantMixin, TimestampMixin, new_id
from taxos_core.workflow.states import WorkItemState


class WorkItem(Base, TenantMixin, TimestampMixin):
    __tablename__ = "work_item"
    __table_args__ = (Index("ix_work_item_state", "tenant_id", "state"),)

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=new_id)
    entity_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("legal_entity.id"), nullable=False
    )
    period_key: Mapped[str] = mapped_column(String(20), nullable=False)
    item_type: Mapped[str] = mapped_column(String(40), nullable=False)  # "VAT_RETURN"
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    computation_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("computation.id"), nullable=True
    )

    state: Mapped[str] = mapped_column(String(30), nullable=False, default=WorkItemState.DRAFT)

    # Who prepared this. The SoD check compares the approver against this value, so it
    # must be recorded even when preparation was agent-driven (the requesting human owns it).
    prepared_by: Mapped[str] = mapped_column(String(255), nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Hash of the reviewable content at the time it entered review. Recomputed on demand;
    # a mismatch means what a reviewer would approve is not what they last saw.
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkflowTransition(Base, TenantMixin):
    """Every state change, kept — the item's own history, independent of the audit chain."""

    __tablename__ = "workflow_transition"
    __table_args__ = (Index("ix_transition_item", "tenant_id", "work_item_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=new_id)
    work_item_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("work_item.id"), nullable=False
    )
    from_state: Mapped[str] = mapped_column(String(30), nullable=False)
    to_state: Mapped[str] = mapped_column(String(30), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Approval(Base, TenantMixin):
    """The legal moment. Append-only: a voided approval is marked, never deleted —
    'this was approved and later invalidated' is a different fact from 'never approved'."""

    __tablename__ = "approval"
    __table_args__ = (Index("ix_approval_item", "tenant_id", "work_item_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=new_id)
    work_item_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("work_item.id"), nullable=False
    )
    approver: Mapped[str] = mapped_column(String(255), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    voided: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
