"""Computation snapshots and lineage (US-301, US-202).

Computations and their lineage are immutable evidence: enforced by trigger, not just
convention. A figure whose provenance can be edited is not evidence.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TENANT_TABLES = ["computation", "computation_line", "computation_line_source"]
APP_ROLE = "taxos_app"


def upgrade() -> None:
    op.create_table(
        "computation",
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
        sa.Column("tax_type", sa.String(20), nullable=False),
        sa.Column("pack_ref", sa.String(50), nullable=False),
        sa.Column("pack_content_hash", sa.String(64), nullable=False),
        sa.Column("engine_version", sa.String(20), nullable=False),
        sa.Column("inputs_hash", sa.String(64), nullable=False),
        sa.Column("result_hash", sa.String(64), nullable=False),
        sa.Column("result", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("batch_ids", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("unmapped_codes", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column(
            "computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "inputs_hash", "pack_ref", name="uq_computation_inputs_pack"
        ),
    )
    op.create_index(
        "ix_computation_entity_period", "computation", ["tenant_id", "entity_id", "period_key"]
    )

    op.create_table(
        "computation_line",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "computation_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("computation.id"),
            nullable=False,
        ),
        sa.Column("box_id", sa.String(20), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("value", sa.Numeric(18, 4), nullable=False),
        sa.Column("derived", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("computation_id", "box_id", name="uq_computation_line_box"),
    )

    op.create_table(
        "computation_line_source",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "line_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("computation_line.id"),
            nullable=False,
        ),
        sa.Column(
            "row_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transaction_row.id"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("vat_code", sa.String(20), nullable=False),
        sa.Column("citation_ref", sa.String(100), nullable=False),
    )
    op.create_index("ix_line_source_line", "computation_line_source", ["tenant_id", "line_id"])
    op.create_index("ix_line_source_row", "computation_line_source", ["tenant_id", "row_id"])

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
        op.execute(f"GRANT SELECT, INSERT ON {table} TO {APP_ROLE}")

    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE}")

    # Computations are evidence: append-only at the database, like the audit chain.
    # Superseding a computation means creating a new one, never editing the old.
    for table in NEW_TENANT_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_append_only
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION taxos_reject_mutation();
            """
        )


def downgrade() -> None:
    for table in NEW_TENANT_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
    op.drop_table("computation_line_source")
    op.drop_table("computation_line")
    op.drop_table("computation")
