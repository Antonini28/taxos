"""Agent run and step records (FR-302).

Steps are append-only: the trace of what an agent did is evidence, and evidence that can
be edited afterwards is not evidence.

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "taxos_app"


def upgrade() -> None:
    op.create_table(
        "agent_run",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True
        ),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column(
            "entity_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("legal_entity.id"),
            nullable=True,
        ),
        sa.Column("period_key", sa.String(20), nullable=True),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("plan", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("requested_by", sa.String(255), nullable=False),
        sa.Column(
            "work_item_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("work_item.id"),
            nullable=True,
        ),
        sa.Column("escalation", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("budget_steps", sa.Integer(), nullable=False),
        sa.Column("steps_used", sa.Integer(), nullable=False),
        sa.Column("cost_gbp", sa.Numeric(10, 4), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
    )
    op.create_index("ix_agent_run_state", "agent_run", ["tenant_id", "state"])

    op.create_table(
        "agent_step",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "run_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_run.id"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("agent", sa.String(50), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("tool_calls", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("output", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("confidence_basis", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("model", sa.String(50), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("cost_gbp", sa.Numeric(10, 4), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_agent_step_run", "agent_step", ["tenant_id", "run_id", "sequence"])

    for table in ("agent_run", "agent_step"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
            WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
            """
        )

    op.execute(f"GRANT SELECT, INSERT, UPDATE ON agent_run TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT ON agent_step TO {APP_ROLE}")
    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE}")

    op.execute(
        """
        CREATE TRIGGER agent_step_append_only
        BEFORE UPDATE OR DELETE ON agent_step
        FOR EACH ROW EXECUTE FUNCTION taxos_reject_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS agent_step_append_only ON agent_step")
    for table in ("agent_run", "agent_step"):
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
    op.drop_table("agent_step")
    op.drop_table("agent_run")
