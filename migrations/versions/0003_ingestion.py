"""Ingestion: batches, transaction rows, quarantine, validation results (US-201).

RLS policies applied to every new tenant-scoped table — the introspection invariant
test would fail the build otherwise, which is the point of having it.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TENANT_TABLES = ["batch", "transaction_row", "quarantine_row", "validation_result"]
APP_ROLE = "taxos_app"


def upgrade() -> None:
    op.create_table(
        "batch",
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
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("accepted_count", sa.Integer(), nullable=False),
        sa.Column("quarantined_count", sa.Integer(), nullable=False),
        sa.Column("control_total", sa.Numeric(18, 4), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "content_hash", "period_key", name="uq_batch_content_period"
        ),
    )
    op.create_index("ix_batch_entity_period", "batch", ["tenant_id", "entity_id", "period_key"])

    op.create_table(
        "transaction_row",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "batch_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("batch.id"),
            nullable=False,
        ),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("row_hash", sa.String(64), nullable=False),
        sa.Column("document_ref", sa.String(100), nullable=False),
        sa.Column("document_date", sa.Date(), nullable=False),
        sa.Column("counterparty", sa.String(255), nullable=False),
        sa.Column("net_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("vat_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("vat_code", sa.String(20), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("source_payload", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_txn_batch", "transaction_row", ["tenant_id", "batch_id"])

    op.create_table(
        "quarantine_row",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "batch_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("batch.id"),
            nullable=False,
        ),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("source_payload", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("failures", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_quarantine_batch", "quarantine_row", ["tenant_id", "batch_id"])

    op.create_table(
        "validation_result",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "batch_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("batch.id"),
            nullable=False,
        ),
        sa.Column("rule_id", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("sample_rows", sa.dialects.postgresql.JSONB(), nullable=False),
    )

    for table in NEW_TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
            WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
            """
        )
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO {APP_ROLE}")

    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE}")

    # Batches are immutable once validated (Phase 2 doc 04 §3): status/counts are set
    # during validation, but the source identity — what file, whose, which period —
    # can never change afterwards, or lineage from a computed figure would be a lie.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION taxos_batch_identity_immutable() RETURNS trigger AS $$
        BEGIN
            IF OLD.content_hash IS DISTINCT FROM NEW.content_hash
               OR OLD.entity_id IS DISTINCT FROM NEW.entity_id
               OR OLD.period_key IS DISTINCT FROM NEW.period_key THEN
                RAISE EXCEPTION 'Batch identity is immutable (content_hash, entity_id, period_key)';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER batch_identity_immutable
        BEFORE UPDATE ON batch
        FOR EACH ROW EXECUTE FUNCTION taxos_batch_identity_immutable();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS batch_identity_immutable ON batch")
    op.execute("DROP FUNCTION IF EXISTS taxos_batch_identity_immutable()")
    for table in NEW_TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
    op.drop_table("validation_result")
    op.drop_table("quarantine_row")
    op.drop_table("transaction_row")
    op.drop_table("batch")
