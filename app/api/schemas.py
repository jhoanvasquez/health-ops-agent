"""API request/response models. Explicit types cross the boundary — no raw dicts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.agent.outputs import Confidence, DecisionPacket, Outcome
from app.db.models import CaseState


class CreateCaseRequest(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=255)
    policy_id: str = Field(min_length=1, max_length=255)
    patient_ref: str = Field(min_length=1, max_length=255)


class CaseCreatedResponse(BaseModel):
    case_id: UUID
    state: CaseState


class CaseStatusResponse(BaseModel):
    case_id: UUID
    state: CaseState
    packet: DecisionPacket | None = None
    review_decision: Outcome | None = None
    review_note: str | None = None
    reviewed_at: datetime | None = None


class CaseSummary(BaseModel):
    """A row in the review queue."""

    case_id: UUID
    policy_id: str
    patient_ref: str
    state: CaseState
    recommended_outcome: Outcome | None = None
    recommended_confidence: Confidence | None = None
    created_at: datetime
    reviewed_at: datetime | None = None


class ReviewRequest(BaseModel):
    decision: Outcome
    note: str = Field(default="", max_length=2000)
