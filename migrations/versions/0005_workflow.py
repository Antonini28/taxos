"""Workflow: work items, transitions, approvals (US-402).

Approvals are append-only apart from voiding: the void columns are the one permitted
update, enforced by a trigger that allows nothing else. "Approved then invalidated" must
remain distinguishable from "never approved", so deletion is never the mechanism.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TENANT_TABLES = ["work_item", "workflow_transition", "approval"]
APP_ROLE = "taxos_app"


def upgrade() -> None:
    op.create_table(
        "work_item",
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
        sa.Column("item_type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column(
            "computation_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("computation.id"),
            nullable=True,
        ),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("prepared_by", sa.String(255), nullable=False),
        sa.Column("assigned_to", sa.String(255), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
    )
    op.create_index("ix_work_item_state", "work_item", ["tenant_id", "state"])

    op.create_table(
        "workflow_transition",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "work_item_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("work_item.id"),
            nullable=False,
        ),
        sa.Column("from_state", sa.String(30), nullable=False),
        sa.Column("to_state", sa.String(30), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_transition_item", "workflow_transition", ["tenant_id", "work_item_id"])

    op.create_table(
        "approval",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "work_item_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("work_item.id"),
            nullable=False,
        ),
        sa.Column("approver", sa.String(255), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("voided", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("void_reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_approval_item", "approval", ["tenant_id", "work_item_id"])

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
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON work_item TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT ON workflow_transition TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON approval TO {APP_ROLE}")
    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE}")

    # Transitions are history: append-only, like the audit chain.
    op.execute(
        """
        CREATE TRIGGER workflow_transition_append_only
        BEFORE UPDATE OR DELETE ON workflow_transition
        FOR EACH ROW EXECUTE FUNCTION taxos_reject_mutation();
        """
    )

    # Approvals permit exactly one kind of update — voiding. Who approved, what they
    # approved, and when can never be rewritten.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION taxos_approval_void_only() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Approvals are append-only: DELETE rejected';
            END IF;
            IF OLD.approver IS DISTINCT FROM NEW.approver
               OR OLD.content_hash IS DISTINCT FROM NEW.content_hash
               OR OLD.work_item_id IS DISTINCT FROM NEW.work_item_id
               OR OLD.granted_at IS DISTINCT FROM NEW.granted_at THEN
                RAISE EXCEPTION 'Approval facts are immutable: only voiding is permitted';
            END IF;
            IF OLD.voided = true AND NEW.voided = false THEN
                RAISE EXCEPTION 'A voided approval cannot be un-voided';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER approval_void_only
        BEFORE UPDATE OR DELETE ON approval
        FOR EACH ROW EXECUTE FUNCTION taxos_approval_void_only();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS approval_void_only ON approval")
    op.execute("DROP FUNCTION IF EXISTS taxos_approval_void_only()")
    op.execute("DROP TRIGGER IF EXISTS workflow_transition_append_only ON workflow_transition")
    for table in NEW_TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
    op.drop_table("approval")
    op.drop_table("workflow_transition")
    op.drop_table("work_item")
