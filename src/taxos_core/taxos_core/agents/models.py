"""Agent run and step records.

Deliberately *our* schema rather than the framework's: LangGraph's checkpoint format is
internal to the runtime and free to change, while this is evidence that must still be
readable years from now (ADR-012).
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from taxos_core.shared.persistence.base import Base, TenantMixin, TimestampMixin, new_id


class RunState:
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    WAITING_INPUT = "WAITING_INPUT"  # escalated: needs a human, resumes from here
    HANDOFF = "HANDOFF"  # terminal success — work item awaits human review
    FAILED = "FAILED"


class AgentRun(Base, TenantMixin, TimestampMixin):
    __tablename__ = "agent_run"
    __table_args__ = (Index("ix_agent_run_state", "tenant_id", "state"),)

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=new_id)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("legal_entity.id"), nullable=True
    )
    period_key: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tax_type: Mapped[str] = mapped_column(String(20), nullable=False, default="VAT")

    state: Mapped[str] = mapped_column(String(20), nullable=False, default=RunState.PLANNING)
    plan: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # The human who asked. Preparation is credited to them, never to the agent — an agent
    # cannot be a party to segregation of duties (see workflow.service).
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)

    work_item_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("work_item.id"), nullable=True
    )
    escalation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Budgets are state, not advice: exhaustion ends the run rather than degrading it.
    budget_steps: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    steps_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_gbp: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=0)

    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="stub")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentStep(Base, TenantMixin):
    """One step of one run: which agent, what it was asked, what it returned, what it cost."""

    __tablename__ = "agent_step"
    __table_args__ = (Index("ix_agent_step_run", "tenant_id", "run_id", "sequence"),)

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=new_id)
    run_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("agent_run.id"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    agent: Mapped[str] = mapped_column(String(50), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # COMPLETED/ESCALATED/FAILED

    tool_calls: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    output: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Confidence always carries its basis: DETERMINISTIC (a tool computed it), GROUNDED
    # (cited sources), or MODEL_JUDGEMENT. A bare percentage is theatre.
    confidence_basis: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)

    model: Mapped[str] = mapped_column(String(50), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_gbp: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=0)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
