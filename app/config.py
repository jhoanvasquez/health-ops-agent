"""Application settings, loaded from the environment.

Secrets live in `.env` (gitignored). See `.env.example` for the contract.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # LLM
    anthropic_api_key: str = Field(default="", repr=False)
    llm_model: str = "claude-opus-4-8"

    # Embeddings (Voyage AI — see ADR 003)
    voyage_api_key: str = Field(default="", repr=False)

    # Infrastructure
    database_url: str = "postgresql+asyncpg://health:change-me-locally@postgres:5432/health_ops"
    rabbitmq_url: str = "amqp://health:change-me-locally@rabbitmq:5672/"
    redis_url: str = "redis://redis:6379/0"


settings = Settings()
