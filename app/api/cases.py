"""Case endpoints: create (enqueue) and query.

Handlers are thin — validate, check idempotency, persist, publish — and never run
the agent inline. Processing happens asynchronously in the worker.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.outputs import DecisionPacket
from app.api.deps import get_db, get_idempotency, get_publisher
from app.api.schemas import CaseCreatedResponse, CaseStatusResponse, CreateCaseRequest
from app.db.models import Case, CaseState
from app.messaging.events import CaseEventPublisher
from app.services.idempotency import IdempotencyGuard

router = APIRouter(prefix="/cases", tags=["cases"])

_IDEMPOTENCY_TTL_SECONDS = 60


async def _find_by_key(session: AsyncSession, key: str) -> Case | None:
    return await session.scalar(select(Case).where(Case.idempotency_key == key))


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


@router.get("/{case_id}", response_model=CaseStatusResponse)
async def get_case(
    case_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> CaseStatusResponse:
    case = await session.get(Case, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "case not found")
    packet = DecisionPacket.model_validate(case.packet) if case.packet is not None else None
    return CaseStatusResponse(case_id=case.id, state=case.state, packet=packet)
