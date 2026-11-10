"""Concrete `PolicyStore` backed by Postgres + pgvector.

Not imported by the tool registry — only wired in at runtime by the worker, so
the registry (and the description check) stay free of database imports.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.ports import PolicyPassage
from app.db.models import PolicyChunk


class PgPolicyStore:
    """Cosine-similarity search over `policy_chunks` for one policy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(
        self, *, policy_id: str, embedding: list[float], top_k: int
    ) -> list[PolicyPassage]:
        distance = PolicyChunk.embedding.cosine_distance(embedding)
        stmt = (
            select(PolicyChunk, distance.label("distance"))
            .where(PolicyChunk.policy_id == policy_id)
            .order_by(distance)
            .limit(top_k)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            PolicyPassage(
                passage=chunk.passage,
                page=chunk.page,
                doc_id=chunk.doc_id,
                score=1.0 - float(distance_value),  # cosine similarity
            )
            for chunk, distance_value in rows
        ]
