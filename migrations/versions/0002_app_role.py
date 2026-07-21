"""Role separation: the application connects as a NON-SUPERUSER (Phase 6 doc 03 §1).

Why this migration exists: superusers and table owners bypass row-level security.
An application connecting as the owner would silently defeat ADR-006 — tenant
isolation would be "enabled" in the schema and absent in reality. Splitting the
roles is what makes RLS a real control:

  taxos       — migration/owner role (DDL only; never used by the app)
  taxos_app   — application role: DML only, RLS FORCED, no BYPASSRLS
  taxos_platform — cross-tenant infrastructure (outbox relay); still no BYPASSRLS,
                   granted explicit policy exemption per table where genuinely needed

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-21

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "taxos_app"
APP_PASSWORD = "taxos_app"  # local/dev only; real environments inject from Key Vault


def upgrade() -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
                CREATE ROLE {APP_ROLE} LOGIN PASSWORD '{APP_PASSWORD}' NOBYPASSRLS;
            END IF;
        END $$;
        """
    )
    op.execute(f"GRANT CONNECT ON DATABASE taxos TO {APP_ROLE}")
    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}")
    # DML only — no DDL, no TRUNCATE: the app cannot reshape its own schema.
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {APP_ROLE}")
    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE}")
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP_ROLE}"
    )
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {APP_ROLE}"
    )
    # ADR-009 at the grant level: the app may append audit rows, never alter them.
    op.execute(f"REVOKE UPDATE, DELETE ON audit_event FROM {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {APP_ROLE}")
    op.execute(f"REVOKE CONNECT ON DATABASE taxos FROM {APP_ROLE}")
    op.execute(f"DROP ROLE IF EXISTS {APP_ROLE}")
