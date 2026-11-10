"""Ports (interfaces) the tools depend on.

Tools depend on these Protocols, never on concrete infrastructure. Concrete
adapters live in `stores.py`, `patient_repo.py`, and `app/ingestion/`. Tests
supply fakes. This keeps the tool code — and the registry the description check
imports — free of database and API-client imports.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel


class PolicyPassage(BaseModel):
    """One retrieved policy passage with its page reference and similarity score."""

    passage: str
    page: int
    doc_id: str
    score: float


class PatientRepository(Protocol):
    """Source of synthetic patient records."""

    async def get(self, patient_ref: str) -> dict[str, Any] | None:
        """Return the patient's FHIR data, or None if the reference is unknown."""
        ...


class Embedder(Protocol):
    """Turns text into an embedding vector."""

    async def embed(self, text: str) -> list[float]: ...


class PolicyStore(Protocol):
    """Semantic search over ingested policy chunks."""

    async def search(
        self, *, policy_id: str, embedding: list[float], top_k: int
    ) -> list[PolicyPassage]:
        """Return the top_k closest passages for a policy, or an empty list."""
        ...
