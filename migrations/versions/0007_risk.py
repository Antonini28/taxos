"""Anomalies and scans (US-801, FR-501/506).

Anomalies are mutable — their status changes when dispositioned — but the disposition is
audited through the unit of work like any other state change, and the detection facts
(explanation, evidence, detector version) are set once at insert and never rewritten.

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "taxos_app"


def upgrade() -> None:
    op.create_table(
        "anomaly",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True
        ),
        sa.Column(
            "entity_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("legal_entity.id"),
            nullable=False,
        ),
        sa.Column("period_key", sa.String(20), nullable=False),
        sa.Column(
            "row_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transaction_row.id"),
            nullable=False,
        ),
        sa.Column("document_ref", sa.String(100), nullable=False),
        sa.Column("detector", sa.String(20), nullable=False),
        sa.Column("detector_version", sa.String(20), nullable=False),
        sa.Column("anomaly_type", sa.String(40), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evidence", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("disposition_reason", sa.String(40), nullable=True),
        sa.Column("disposition_note", sa.Text(), nullable=True),
        sa.Column("dispositioned_by", sa.String(255), nullable=True),
        sa.Column("dispositioned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
    )
    op.create_index("ix_anomaly_status", "anomaly", ["tenant_id", "status"])
    op.create_index("ix_anomaly_entity_period", "anomaly", ["tenant_id", "entity_id", "period_key"])

    op.create_table(
        "anomaly_scan",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True
        ),
        sa.Column(
            "entity_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("legal_entity.id"),
            nullable=False,
        ),
        sa.Column("period_key", sa.String(20), nullable=False),
        sa.Column("detector_version", sa.String(20), nullable=False),
        sa.Column("rows_scanned", sa.Integer(), nullable=False),
        sa.Column("flagged", sa.Integer(), nullable=False),
        sa.Column(
            "completed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
    )

    for table in ("anomaly", "anomaly_scan"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
            WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
            """
        )
    # Anomalies are dispositioned (UPDATE); scans are write-once.
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON anomaly TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT ON anomaly_scan TO {APP_ROLE}")
    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE}")


def downgrade() -> None:
    for table in ("anomaly", "anomaly_scan"):
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
    op.drop_table("anomaly_scan")
    op.drop_table("anomaly")
