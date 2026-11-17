"""Tests for settings normalization — the async Postgres driver rewrite."""

from __future__ import annotations

import pytest

from app.config import Settings


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "postgresql://user:pw@host:5432/db",
            "postgresql+asyncpg://user:pw@host:5432/db",
        ),
        (
            "postgres://user:pw@host:5432/db",
            "postgresql+asyncpg://user:pw@host:5432/db",
        ),
        (
            "postgresql+asyncpg://user:pw@host:5432/db",
            "postgresql+asyncpg://user:pw@host:5432/db",
        ),
    ],
)
def test_database_url_normalized_to_asyncpg(raw: str, expected: str) -> None:
    assert Settings(database_url=raw).database_url == expected


def test_query_params_are_preserved() -> None:
    settings = Settings(database_url="postgresql://user:pw@host:5432/db?ssl=require")
    assert settings.database_url == "postgresql+asyncpg://user:pw@host:5432/db?ssl=require"
