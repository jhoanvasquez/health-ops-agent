"""FastAPI dependencies: DB session, event publisher, idempotency guard.

The publisher and guard are created once in the app lifespan and read here from
`app.state`, so handlers depend on the ports, not the concrete clients.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import SessionFactory
from app.messaging.events import CaseEventPublisher
from app.services.idempotency import IdempotencyGuard


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session


def get_publisher(request: Request) -> CaseEventPublisher:
    return cast(CaseEventPublisher, request.app.state.publisher)


def get_idempotency(request: Request) -> IdempotencyGuard:
    return cast(IdempotencyGuard, request.app.state.idempotency)
