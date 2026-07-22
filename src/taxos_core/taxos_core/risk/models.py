"""Anomaly records and their dispositions.

An anomaly stores its explanation and detector version at detection time (FR-502): you
cannot faithfully reconstruct why something was flagged after the rules have moved, so the
reasoning is captured with the flag. Dispositions are reason-coded — and the reason
matters: a legitimate recurring instalment dismissed as RECURRING_CONTRACT is a true
negative, while DISMISSED_NO_TIME is a censored label, not a benign one (docs/ml/03 §2).
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from taxos_core.shared.persistence.base import Base, TenantMixin, TimestampMixin, new_id


class AnomalyStatus:
    OPEN = "OPEN"
    CONFIRMED = "CONFIRMED"
    DISMISSED = "DISMISSED"


# Reason codes are structured, not free text: they are the label taxonomy a supervised
# model would train on, so their meaning must be stable and their true/censored nature
# explicit (docs/ml/03 §2).
CONFIRM_REASONS = {
    "GENUINE_DUPLICATE": "A genuinely duplicated payment",
    "MISCLASSIFIED": "Incorrect tax treatment confirmed",
    "REQUIRES_INVESTIGATION": "Escalated for further investigation",
}
DISMISS_REASONS = {
    "RECURRING_CONTRACT": "Legitimate recurring instalment (true negative)",
    "DIFFERENT_SUPPLY": "Similar amount, genuinely different supply (true negative)",
    "REVIEWED_ACCEPTABLE": "Reviewed and acceptable (true negative)",
    "NO_TIME": "Not investigated — capacity (censored, not a true negative)",
}


class Anomaly(Base, TenantMixin, TimestampMixin):
    __tablename__ = "anomaly"
    __table_args__ = (
        Index("ix_anomaly_status", "tenant_id", "status"),
        Index("ix_anomaly_entity_period", "tenant_id", "entity_id", "period_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=new_id)
    entity_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("legal_entity.id"), nullable=False
    )
    period_key: Mapped[str] = mapped_column(String(20), nullable=False)

    row_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("transaction_row.id"), nullable=False
    )
    document_ref: Mapped[str] = mapped_column(String(100), nullable=False)

    detector: Mapped[str] = mapped_column(String(20), nullable=False)
    detector_version: Mapped[str] = mapped_column(String(20), nullable=False)
    anomaly_type: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)

    # Captured at detection time — this is what the reviewer saw when they decided.
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default=AnomalyStatus.OPEN)
    disposition_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)
    disposition_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    dispositioned_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dispositioned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AnomalyScan(Base, TenantMixin, TimestampMixin):
    """A scan run: what was scanned, by which detector version, and how many it flagged.

    Recorded so 'no anomalies' and 'no scan' are never confused — an empty result from a
    real scan is a different fact from a scan that never happened (docs/ai/03 §3.4)."""

    __tablename__ = "anomaly_scan"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=new_id)
    entity_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("legal_entity.id"), nullable=False
    )
    period_key: Mapped[str] = mapped_column(String(20), nullable=False)
    detector_version: Mapped[str] = mapped_column(String(20), nullable=False)
    rows_scanned: Mapped[int] = mapped_column(nullable=False, default=0)
    flagged: Mapped[int] = mapped_column(nullable=False, default=0)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RiskScore(Base, TenantMixin, TimestampMixin):
    """A Rung-2 model score for one transaction, with its exact Shapley explanation stored
    at scoring time (docs/ml/04). Advisory, never a disposition: a reviewer weighs the score
    and its reason, then acts on the transaction elsewhere (ML-1). Scores are a deterministic
    function of the population and the model version, so re-scoring replaces them rather than
    accumulating history — the model_version pins which model produced a stored score."""

    __tablename__ = "risk_score"
    __table_args__ = (Index("ix_risk_score_entity_period", "tenant_id", "entity_id", "period_key"),)

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=new_id)
    entity_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("legal_entity.id"), nullable=False
    )
    period_key: Mapped[str] = mapped_column(String(20), nullable=False)
    row_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("transaction_row.id"), nullable=False
    )
    document_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    counterparty: Mapped[str] = mapped_column(String(255), nullable=False)

    model_version: Mapped[str] = mapped_column(String(30), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    percentile: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    # [{feature, value, contribution}] — the exact Shapley attribution, top-first.
    attributions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
