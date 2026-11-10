"""Unit tests for the agent tools, using in-memory fakes for the ports."""

from __future__ import annotations

from typing import Any

import pytest

from app.agent.tools.base import ToolContext, ToolError, invoke
from app.agent.tools.get_patient import GetPatientTool
from app.agent.tools.ports import PolicyPassage
from app.agent.tools.registry import BY_NAME, REGISTRY
from app.agent.tools.search_policy import SearchPolicyTool


class FakePatients:
    def __init__(self, data: dict[str, dict[str, Any]]) -> None:
        self._data = data

    async def get(self, patient_ref: str) -> dict[str, Any] | None:
        return self._data.get(patient_ref)


class FakeEmbedder:
    async def embed(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


class FakePolicyStore:
    def __init__(self, passages: list[PolicyPassage]) -> None:
        self._passages = passages
        self.last_top_k: int | None = None

    async def search(
        self, *, policy_id: str, embedding: list[float], top_k: int
    ) -> list[PolicyPassage]:
        self.last_top_k = top_k
        return self._passages[:top_k]


def make_ctx(
    *,
    patients: dict[str, dict[str, Any]] | None = None,
    passages: list[PolicyPassage] | None = None,
) -> ToolContext:
    return ToolContext(
        patients=FakePatients(patients or {}),
        policy_store=FakePolicyStore(passages or []),
        embedder=FakeEmbedder(),
    )


async def test_get_patient_found() -> None:
    ctx = make_ctx(patients={"patient-001": {"resourceType": "Patient", "id": "001"}})
    result = await invoke(GetPatientTool(), {"patient_ref": "patient-001"}, ctx)
    assert result == {"resourceType": "Patient", "id": "001"}


async def test_get_patient_not_found_returns_error() -> None:
    ctx = make_ctx(patients={})
    result = await invoke(GetPatientTool(), {"patient_ref": "ghost"}, ctx)
    assert isinstance(result, ToolError)
    assert result.retryable is False


async def test_search_policy_returns_passages() -> None:
    passages = [PolicyPassage(passage="MRI requires prior X-ray.", page=2, doc_id="d1", score=0.9)]
    ctx = make_ctx(passages=passages)
    result = await invoke(
        SearchPolicyTool(), {"query": "imaging", "policy_id": "p1", "top_k": 5}, ctx
    )
    assert result == passages


async def test_search_policy_empty_is_empty_list() -> None:
    ctx = make_ctx(passages=[])
    result = await invoke(SearchPolicyTool(), {"query": "x", "policy_id": "p1"}, ctx)
    assert result == []


async def test_invalid_input_returns_non_retryable_error() -> None:
    ctx = make_ctx()
    result = await invoke(
        SearchPolicyTool(), {"query": "x", "policy_id": "p1", "top_k": 99}, ctx
    )
    assert isinstance(result, ToolError)
    assert result.retryable is False


def test_every_registered_tool_has_complete_description() -> None:
    for tool in REGISTRY:
        desc = tool.description.lower()
        assert len(tool.description) >= 120
        for phrase in ("use when", "do not use", "input", "returns"):
            assert phrase in desc, f"{tool.name} missing {phrase!r}"


def test_registry_is_indexed_by_name() -> None:
    assert set(BY_NAME) == {"get_patient", "search_policy"}


if __name__ == "__main__":  # allow running without pytest-asyncio
    raise SystemExit(pytest.main([__file__, "-q"]))
