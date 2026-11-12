"""human review: review_decision, review_note, reviewer, reviewed_at

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("cases", sa.Column("review_decision", sa.String(16), nullable=True))
    op.add_column("cases", sa.Column("review_note", sa.String(2000), nullable=True))
    op.add_column("cases", sa.Column("reviewer", sa.String(255), nullable=True))
    op.add_column("cases", sa.Column("reviewed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("cases", "reviewed_at")
    op.drop_column("cases", "reviewer")
    op.drop_column("cases", "review_note")
    op.drop_column("cases", "review_decision")
