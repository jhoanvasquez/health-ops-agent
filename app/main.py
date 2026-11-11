"""FastAPI application entrypoint.

Wires the case endpoints and connects the event publisher and idempotency guard
for the lifetime of the process.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel
from redis.asyncio import Redis

from app import __version__
from app.api import cases
from app.config import settings
from app.messaging.events import RabbitPublisher
from app.services.idempotency import RedisIdempotencyGuard


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    publisher = await RabbitPublisher.connect(settings.rabbitmq_url)
    redis = Redis.from_url(settings.redis_url)
    app.state.publisher = publisher
    app.state.idempotency = RedisIdempotencyGuard(redis)
    try:
        yield
    finally:
        await publisher.close()
        await redis.aclose()


app = FastAPI(title="Health Operations Agent", version=__version__, lifespan=lifespan)
app.include_router(cases.router)


class HealthResponse(BaseModel):
    status: str
    version: str
    env: str


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe. Returns service status, version, and environment."""
    return HealthResponse(status="ok", version=__version__, env=settings.env)
