"""reliability: failed state, attempts, last_error

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ADD VALUE is safe inside a transaction on Postgres 12+ as long as the new
    # value is not used in the same transaction (we only add columns here).
    op.execute("ALTER TYPE case_state ADD VALUE IF NOT EXISTS 'failed'")
    op.add_column(
        "cases",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("cases", sa.Column("last_error", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("cases", "last_error")
    op.drop_column("cases", "attempts")
    # Postgres cannot easily drop an enum value; 'failed' is left in place.
