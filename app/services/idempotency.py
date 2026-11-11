"""Idempotency guard — a port over a fast key store (Redis).

The API handler depends on the `IdempotencyGuard` protocol, not on Redis, so the
handler stays testable with a fake and the DB unique constraint remains the
durable source of truth. The guard only closes the race between two concurrent
duplicate requests.
"""

from __future__ import annotations

from typing import Any, Protocol


class IdempotencyGuard(Protocol):
    async def acquire(self, key: str, ttl_seconds: int) -> bool:
        """Return True if this caller won the key, False if it is already held."""
        ...


class RedisIdempotencyGuard:
    """Concrete guard: `SET key 1 NX EX ttl`."""

    def __init__(self, redis: Any) -> None:  # redis.asyncio.Redis — Any at this boundary
        self._redis = redis

    async def acquire(self, key: str, ttl_seconds: int) -> bool:
        return bool(await self._redis.set(f"idem:{key}", "1", nx=True, ex=ttl_seconds))
