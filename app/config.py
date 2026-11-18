"""Application settings, loaded from the environment.

Secrets live in `.env` (gitignored). See `.env.example` for the contract.
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ASYNC_PG_DRIVER = "postgresql+asyncpg://"


class Settings(BaseSettings):
    """Typed, validated configuration for the service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    env: str = "local"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]
    # Co-host the queue consumer inside the API process. Off locally (a dedicated
    # worker runs via compose); on where the platform has no separate worker process
    # (e.g. Render's free tier, which does not offer background workers).
    embed_worker: bool = False

    # LLM
    anthropic_api_key: str = Field(default="", repr=False)
    llm_model: str = "claude-opus-4-8"

    # Embeddings (Voyage AI — see ADR 003)
    voyage_api_key: str = Field(default="", repr=False)

    # Infrastructure
    database_url: str = "postgresql+asyncpg://health:change-me-locally@postgres:5432/health_ops"
    rabbitmq_url: str = "amqp://health:change-me-locally@rabbitmq:5672/"
    redis_url: str = "redis://redis:6379/0"

    @field_validator("database_url")
    @classmethod
    def _use_async_driver(cls, value: str) -> str:
        """Normalize a managed-Postgres URL to the asyncpg driver.

        Render (and most managed Postgres) expose ``postgres://`` or
        ``postgresql://``; SQLAlchemy async and Alembic need the explicit
        ``postgresql+asyncpg://`` driver. An already-async URL is left untouched.
        """
        for prefix in ("postgresql://", "postgres://"):
            if value.startswith(prefix):
                return _ASYNC_PG_DRIVER + value[len(prefix) :]
        return value


settings = Settings()
