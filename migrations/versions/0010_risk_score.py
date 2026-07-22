"""Risk scores — the Rung-2 model's advisory output, with stored Shapley explanations.

Tenant-scoped under RLS like every business table. Scores are a deterministic function of
the population and model version, so re-scoring DELETEs the prior set and inserts fresh — the
app role is granted DELETE here for exactly that (anomalies, by contrast, are never deleted:
they carry human dispositions).

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "taxos_app"


def upgrade() -> None:
    op.create_table(
        "risk_score",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.Column("counterparty", sa.String(255), nullable=False),
        sa.Column("model_version", sa.String(30), nullable=False),
        sa.Column("score", sa.Numeric(10, 6), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("percentile", sa.Numeric(5, 4), nullable=False),
        sa.Column("flagged", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("attributions", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
    )
    op.create_index(
        "ix_risk_score_entity_period", "risk_score", ["tenant_id", "entity_id", "period_key"]
    )

    op.execute("ALTER TABLE risk_score ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE risk_score FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY risk_score_tenant_isolation ON risk_score
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        """
    )
    # Deterministic advisory output: re-scoring replaces the set, so DELETE is granted.
    op.execute(f"GRANT SELECT, INSERT, DELETE ON risk_score TO {APP_ROLE}")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS risk_score_tenant_isolation ON risk_score")
    op.drop_table("risk_score")
