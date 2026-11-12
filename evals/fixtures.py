"""In-memory fixtures that satisfy the tool ports — no database, no Voyage.

These let the eval harness build a real `ToolContext` from a case file, so the
agent runs exactly as in production but on deterministic, self-contained inputs.
"""

from __future__ import annotations

from typing import Any

from app.agent.tools.ports import PolicyPassage
from app.llm.types import LLMResponse, Message, ToolSpec
from evals.dataset import CasePassage


class FixturePatientRepository:
    """Returns the case's patient for any reference."""

    def __init__(self, patient: dict[str, Any]) -> None:
        self._patient = patient

    async def get(self, patient_ref: str) -> dict[str, Any] | None:
        return self._patient


class FixturePolicyStore:
    """Returns the case's passages (retrieval stand-in), ignoring the query embedding."""

    def __init__(self, passages: list[CasePassage]) -> None:
        self._passages = [
            PolicyPassage(passage=p.passage, page=p.page, doc_id=p.doc_id, score=1.0)
            for p in passages
        ]

    async def search(
        self, *, policy_id: str, embedding: list[float], top_k: int
    ) -> list[PolicyPassage]:
        return self._passages[:top_k]


class StubEmbedder:
    """A no-op embedder; the fixture store ignores the vector, so Voyage is never called."""

    async def embed(self, text: str) -> list[float]:
        return [0.0]


class ReplayLLM:
    """A scripted `LLMClient` that replays a fixed list of responses, one per call.

    Used by `--self-check` to drive the real harness deterministically — no network.
    """

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = responses
        self._index = 0

    async def complete(
        self, *, system: str, messages: list[Message], tools: list[ToolSpec], max_tokens: int
    ) -> LLMResponse:
        response = self._responses[self._index]
        self._index += 1
        return response
