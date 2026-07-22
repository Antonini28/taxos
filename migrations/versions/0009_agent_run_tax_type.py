"""Agent runs carry their tax type, so one runtime prepares any tax (AP-3).

A run is now for VAT or Corporation Tax (or a future type). The Supervisor reads this to
choose the data check, the compute step, and the kind of work item it hands off — none of
which is hardcoded to VAT any longer. Existing rows default to VAT, which is what they were.

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_run",
        sa.Column("tax_type", sa.String(20), nullable=False, server_default="VAT"),
    )


def downgrade() -> None:
    op.drop_column("agent_run", "tax_type")
