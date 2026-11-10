"""FastAPI application entrypoint.

Phase 0 bootstrap: exposes a health endpoint so the stack is verifiably up.
Case endpoints (`POST /cases`, `GET /cases/{id}`) arrive in the first E2E slice.
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from app import __version__
from app.config import settings

app = FastAPI(title="Health Operations Agent", version=__version__)


class HealthResponse(BaseModel):
    status: str
    version: str
    env: str


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe. Returns service status, version, and environment."""
    return HealthResponse(status="ok", version=__version__, env=settings.env)
