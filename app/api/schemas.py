"""API request/response models. Explicit types cross the boundary — no raw dicts."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.agent.outputs import DecisionPacket
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
