"""FastAPI application entrypoint.

Wires the case endpoints and connects the event publisher and idempotency guard
for the lifetime of the process.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from redis.asyncio import Redis

from app import __version__
from app.api import cases, policies
from app.config import settings
from app.messaging.events import RabbitPublisher
from app.services.idempotency import RedisIdempotencyGuard
from app.workers.case_worker import start_consumer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    publisher = await RabbitPublisher.connect(settings.rabbitmq_url)
    redis = Redis.from_url(settings.redis_url)
    app.state.publisher = publisher
    app.state.idempotency = RedisIdempotencyGuard(redis)
    # On platforms with no separate worker process (e.g. Render free tier), co-host
    # the queue consumer here so submitted cases actually get processed.
    consumer = await start_consumer() if settings.embed_worker else None
    try:
        yield
    finally:
        if consumer is not None:
            await consumer.close()
        await publisher.close()
        await redis.aclose()


app = FastAPI(title="Health Operations Agent", version=__version__, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(cases.router)
app.include_router(policies.router)


class HealthResponse(BaseModel):
    status: str
    version: str
    env: str


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe. Returns service status, version, and environment."""
    return HealthResponse(status="ok", version=__version__, env=settings.env)
