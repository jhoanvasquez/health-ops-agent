"""initial schema: cases, audit_entries, policy_chunks

Revision ID: 0001
Revises:
Create Date: 2026-11-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 1024

_CASE_STATE = sa.Enum(
    "received",
    "processing",
    "needs_human",
    "request_info",
    "decided",
    name="case_state",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "cases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("state", _CASE_STATE, nullable=False),
        sa.Column("policy_id", sa.String(255), nullable=False),
        sa.Column("patient_ref", sa.String(255), nullable=False),
        sa.Column("packet", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_cases_idempotency_key", "cases", ["idempotency_key"], unique=True)
    op.create_index("ix_cases_state", "cases", ["state"])
    op.create_index("ix_cases_policy_id", "cases", ["policy_id"])

    op.create_table(
        "audit_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "case_id",
            sa.Uuid(),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("tool", sa.String(255), nullable=False),
        sa.Column("input_redacted", postgresql.JSONB(), nullable=False),
        sa.Column("output_redacted", postgresql.JSONB(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_entries_case_id", "audit_entries", ["case_id"])

    op.create_table(
        "policy_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("policy_id", sa.String(255), nullable=False),
        sa.Column("doc_id", sa.String(255), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("passage", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
    )
    op.create_index("ix_policy_chunks_policy_id", "policy_chunks", ["policy_id"])
    op.create_index("ix_policy_chunks_doc_id", "policy_chunks", ["doc_id"])


def downgrade() -> None:
    op.drop_table("policy_chunks")
    op.drop_table("audit_entries")
    op.drop_table("cases")
    op.execute("DROP TYPE IF EXISTS case_state")
