"""Embedding adapter (Voyage AI, see ADR 003).

Implements the `Embedder` port. `input_type` distinguishes document ingestion
from query embedding, which Voyage uses to improve retrieval quality.
"""

from __future__ import annotations

from typing import Literal

import voyageai

from app.config import settings

EMBEDDING_MODEL = "voyage-3"
EMBEDDING_DIM = 1024


class VoyageEmbedder:
    """Concrete `Embedder` backed by the Voyage API."""

    def __init__(
        self,
        *,
        model: str = EMBEDDING_MODEL,
        input_type: Literal["document", "query"] = "query",
        api_key: str | None = None,
    ) -> None:
        self._model = model
        self._input_type = input_type
        self._client = voyageai.AsyncClient(api_key=api_key or settings.voyage_api_key)

    async def embed(self, text: str) -> list[float]:
        result = await self._client.embed(
            [text], model=self._model, input_type=self._input_type
        )
        vector: list[float] = result.embeddings[0]
        return vector
