"""ORM models: Case, AuditEntry, PolicyChunk.

Case state machine (design D6):
    received -> processing -> (decided | needs_human | request_info)

Embedding dimension is fixed here so migrations are deterministic; the embedding
provider/model is finalized in the ingestion change (Phase 2).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

EMBEDDING_DIM = 1024  # voyage-3 default; finalized in the ingestion change


class CaseState(str, enum.Enum):
    """Explicit, persisted case lifecycle."""

    received = "received"
    processing = "processing"
    needs_human = "needs_human"
    request_info = "request_info"
    decided = "decided"


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    state: Mapped[CaseState] = mapped_column(
        SAEnum(CaseState, name="case_state"),
        default=CaseState.received,
        index=True,
    )
    policy_id: Mapped[str] = mapped_column(String(255), index=True)
    patient_ref: Mapped[str] = mapped_column(String(255))
    # Final DecisionPacket (see app/agent/outputs.py), null until decided.
    packet: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    audit_entries: Mapped[list[AuditEntry]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="AuditEntry.step",
    )


class AuditEntry(Base):
    """Append-only record of one agent step. Inputs/outputs are redacted (no PHI)."""

    __tablename__ = "audit_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )
    step: Mapped[int] = mapped_column(Integer)
    tool: Mapped[str] = mapped_column(String(255))
    input_redacted: Mapped[dict[str, Any]] = mapped_column(JSONB)
    output_redacted: Mapped[dict[str, Any]] = mapped_column(JSONB)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    case: Mapped[Case] = relationship(back_populates="audit_entries")


class PolicyChunk(Base):
    """A chunk of a payer policy document, with page reference and embedding."""

    __tablename__ = "policy_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[str] = mapped_column(String(255), index=True)
    doc_id: Mapped[str] = mapped_column(String(255), index=True)
    page: Mapped[int] = mapped_column(Integer)
    passage: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
