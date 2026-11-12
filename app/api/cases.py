"""Case endpoints: create (enqueue), query, list the review queue, and record a review.

Handlers are thin — validate, check idempotency, persist, publish — and never run
the agent inline. Processing happens asynchronously in the worker.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.outputs import Confidence, DecisionPacket, Outcome
from app.api.deps import get_db, get_idempotency, get_publisher
from app.api.schemas import (
    CaseCreatedResponse,
    CaseStatusResponse,
    CaseSummary,
    CreateCaseRequest,
    ReviewRequest,
)
from app.db.models import AuditEntry, Case, CaseState
from app.messaging.events import CaseEventPublisher
from app.services.idempotency import IdempotencyGuard

router = APIRouter(prefix="/cases", tags=["cases"])

_IDEMPOTENCY_TTL_SECONDS = 60
_STUB_REVIEWER = "reviewer"  # auth / RBAC is a separate change


async def _find_by_key(session: AsyncSession, key: str) -> Case | None:
    return await session.scalar(select(Case).where(Case.idempotency_key == key))


def _to_status(case: Case) -> CaseStatusResponse:
    packet = DecisionPacket.model_validate(case.packet) if case.packet is not None else None
    return CaseStatusResponse(
        case_id=case.id,
        state=case.state,
        packet=packet,
        review_decision=cast("Outcome | None", case.review_decision),
        review_note=case.review_note,
        reviewed_at=case.reviewed_at,
    )


def _to_summary(case: Case) -> CaseSummary:
    packet = case.packet or {}
    return CaseSummary(
        case_id=case.id,
        policy_id=case.policy_id,
        patient_ref=case.patient_ref,
        state=case.state,
        recommended_outcome=cast("Outcome | None", packet.get("outcome")),
        recommended_confidence=cast("Confidence | None", packet.get("confidence")),
        created_at=case.created_at,
        reviewed_at=case.reviewed_at,
    )


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=CaseCreatedResponse)
async def create_case(
    body: CreateCaseRequest,
    session: AsyncSession = Depends(get_db),
    publisher: CaseEventPublisher = Depends(get_publisher),
    idempotency: IdempotencyGuard = Depends(get_idempotency),
) -> CaseCreatedResponse:
    existing = await _find_by_key(session, body.idempotency_key)
    if existing is not None:
        return CaseCreatedResponse(case_id=existing.id, state=existing.state)

    if not await idempotency.acquire(body.idempotency_key, _IDEMPOTENCY_TTL_SECONDS):
        existing = await _find_by_key(session, body.idempotency_key)
        if existing is not None:
            return CaseCreatedResponse(case_id=existing.id, state=existing.state)
        raise HTTPException(status.HTTP_409_CONFLICT, "a duplicate request is in progress")

    case_id = uuid4()
    session.add(
        Case(
            id=case_id,
            idempotency_key=body.idempotency_key,
            policy_id=body.policy_id,
            patient_ref=body.patient_ref,
            state=CaseState.received,
        )
    )
    await session.commit()
    await publisher.publish_case(str(case_id))
    return CaseCreatedResponse(case_id=case_id, state=CaseState.received)


@router.get("", response_model=list[CaseSummary])
async def list_cases(
    pending_review: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
) -> list[CaseSummary]:
    stmt = select(Case)
    if pending_review:
        stmt = stmt.where(Case.state == CaseState.needs_human, Case.review_decision.is_(None))
    stmt = stmt.order_by(Case.created_at.desc()).limit(limit)
    result = await session.scalars(stmt)
    return [_to_summary(case) for case in result.all()]


@router.get("/{case_id}", response_model=CaseStatusResponse)
async def get_case(
    case_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> CaseStatusResponse:
    case = await session.get(Case, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "case not found")
    return _to_status(case)


@router.post("/{case_id}/review", response_model=CaseStatusResponse)
async def review_case(
    case_id: UUID,
    body: ReviewRequest,
    session: AsyncSession = Depends(get_db),
) -> CaseStatusResponse:
    case = await session.get(Case, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "case not found")
    if case.review_decision is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "case already reviewed")

    case.review_decision = body.decision
    case.review_note = body.note
    case.reviewer = _STUB_REVIEWER
    case.reviewed_at = datetime.now(UTC)
    session.add(
        AuditEntry(
            case_id=case.id,
            step=0,
            tool="human_review",
            input_redacted={"decision": body.decision},
            output_redacted={"reviewer": _STUB_REVIEWER},
        )
    )
    await session.commit()
    return _to_status(case)
