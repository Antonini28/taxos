"""Foundation: master data, audit chain, outbox — with RLS and immutability guards.

Hand-authored (autogenerate is a draft, not an author — Phase 6 doc 03 §5): RLS
policies, triggers, and REVOKEs are exactly what autogenerate misses, and they are
the migration's most important content.

Implements: ADR-006 (RLS tenancy), ADR-009 (append-only audit chain), ADR-003 (outbox).

Revision ID: 0001
Revises:
Create Date: 2026-07-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Every business (tenant-scoped) table gets an RLS policy. The CI invariant test
# `test_every_business_table_has_rls_policy` reads this same list — a new table
# without a policy fails the build.
TENANT_SCOPED_TABLES = ["legal_entity", "tax_registration", "audit_event", "outbox_event"]


def upgrade() -> None:
    # --- reference data (global, not tenant-scoped) ---
    op.create_table(
        "jurisdiction",
        sa.Column("code", sa.String(10), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
    )
    op.execute("INSERT INTO jurisdiction (code, name) VALUES ('UK', 'United Kingdom')")

    op.create_table(
        "tenant",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
    )

    # --- tenant-scoped business tables ---
    op.create_table(
        "legal_entity",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True
        ),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "jurisdiction_code", sa.String(10), sa.ForeignKey("jurisdiction.code"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.UniqueConstraint("tenant_id", "code", name="uq_legal_entity_tenant_code"),
    )

    op.create_table(
        "tax_registration",
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
        sa.Column("tax_type", sa.String(20), nullable=False),
        sa.Column("registration_number", sa.String(50), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "entity_id", "tax_type", name="uq_registration_entity_tax"
        ),
    )

    # --- audit chain (ADR-009) ---
    op.create_table(
        "audit_event",
        sa.Column("seq", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("subject_type", sa.String(50), nullable=False),
        sa.Column("subject_id", sa.String(100), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("before", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("after", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("event_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("serializer_version", sa.String(10), nullable=False),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_audit_event_tenant_seq", "audit_event", ["tenant_id", "seq"])
    op.create_index(
        "ix_audit_event_subject", "audit_event", ["tenant_id", "subject_type", "subject_id"]
    )

    # --- outbox (ADR-003) ---
    op.create_table(
        "outbox_event",
        sa.Column("seq", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "event_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, unique=True
        ),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("payload", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_outbox_unpublished", "outbox_event", ["published_at", "seq"])

    # --- ADR-006: row-level security on every tenant-scoped table ---
    # Policies read the transaction-local GUC set by tenant_session(). A session that
    # never sets it sees zero rows: fail closed.
    for table in TENANT_SCOPED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
            WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
            """
        )

    # --- ADR-009: append-only enforcement at the database, not just in code ---
    op.execute(
        """
        CREATE OR REPLACE FUNCTION taxos_reject_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Table % is append-only (ADR-009): % rejected',
                TG_TABLE_NAME, TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_event_append_only
        BEFORE UPDATE OR DELETE ON audit_event
        FOR EACH ROW EXECUTE FUNCTION taxos_reject_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_event_append_only ON audit_event")
    op.execute("DROP FUNCTION IF EXISTS taxos_reject_mutation()")
    for table in TENANT_SCOPED_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
    op.drop_table("outbox_event")
    op.drop_table("audit_event")
    op.drop_table("tax_registration")
    op.drop_table("legal_entity")
    op.drop_table("tenant")
    op.drop_table("jurisdiction")
