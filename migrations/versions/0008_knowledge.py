"""Knowledge corpus — global reference data with full-text search (Phase 4).

Not tenant-scoped: like `jurisdiction`, the corpus is shared reference data, so no
tenant_id and no RLS. The search_vector is a Postgres GENERATED column — the FTS index is
a property of the data, maintained by the database, not by application code that might
forget. A GIN index makes retrieval fast.

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "taxos_app"


def upgrade() -> None:
    op.create_table(
        "knowledge_doc",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("authority_rank", sa.String(4), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("citation_ref", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("jurisdiction", sa.String(10), nullable=False),
        sa.Column("tax_domain", sa.String(20), nullable=False),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
    )

    op.create_table(
        "knowledge_chunk",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "doc_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_doc.id"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("heading", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
    )

    # Generated FTS column: heading weighted above body, so a passage whose heading matches
    # the query ranks higher — a small relevance win that keeps the demo's answers sharp.
    op.execute(
        """
        ALTER TABLE knowledge_chunk ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(heading, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(body, '')), 'B')
        ) STORED
        """
    )
    op.execute("CREATE INDEX ix_knowledge_chunk_fts ON knowledge_chunk USING GIN (search_vector)")

    # Global read-only reference data for the app role.
    op.execute(f"GRANT SELECT, INSERT ON knowledge_doc TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT ON knowledge_chunk TO {APP_ROLE}")


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunk_fts", table_name="knowledge_chunk")
    op.drop_table("knowledge_chunk")
    op.drop_table("knowledge_doc")
