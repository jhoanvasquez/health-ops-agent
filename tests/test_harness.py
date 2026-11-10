"""Harness tests driven by a scripted fake LLM — no network, no database."""

from __future__ import annotations

from typing import Any

from app.agent.harness import HarnessLimits, run_case
from app.agent.tools.base import ToolContext
from app.agent.tools.ports import PolicyPassage
from app.llm.types import LLMResponse, Message, ToolCall, ToolSpec, Usage

PASSAGE = PolicyPassage(
    passage="MRI of the knee requires a prior failed course of physical therapy.",
    page=2,
    doc_id="policy-1",
    score=0.95,
)
REAL_EXCERPT = "MRI of the knee requires a prior failed course of physical therapy."


class FakeLLM:
    """Replays a fixed list of responses, one per `complete` call."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = responses
        self.calls = 0

    async def complete(
        self, *, system: str, messages: list[Message], tools: list[ToolSpec], max_tokens: int
    ) -> LLMResponse:
        response = self._responses[self.calls]
        self.calls += 1
        return response


class FakePatients:
    async def get(self, patient_ref: str) -> dict[str, Any] | None:
        return {"resourceType": "Patient", "id": patient_ref}


class FakeEmbedder:
    async def embed(self, text: str) -> list[float]:
        return [0.0, 0.1, 0.2]


class FakeStore:
    def __init__(self, passages: list[PolicyPassage]) -> None:
        self._passages = passages

    async def search(
        self, *, policy_id: str, embedding: list[float], top_k: int
    ) -> list[PolicyPassage]:
        return self._passages[:top_k]


def ctx(passages: list[PolicyPassage] | None = None) -> ToolContext:
    return ToolContext(FakePatients(), FakeStore(passages or []), FakeEmbedder())


def _call(name: str, args: dict[str, Any], *, in_tok: int = 10, out_tok: int = 10) -> LLMResponse:
    return LLMResponse(
        tool_calls=[ToolCall(id=f"call-{name}", name=name, arguments=args)],
        usage=Usage(input_tokens=in_tok, output_tokens=out_tok),
        stop_reason="tool_use",
    )


def _search(policy_id: str = "policy-1") -> LLMResponse:
    return _call("search_policy", {"query": "MRI knee", "policy_id": policy_id, "top_k": 5})


def _decision(outcome: str, confidence: str, met: Any, excerpt: str | None) -> LLMResponse:
    evidence = [] if excerpt is None else [{"doc_id": "policy-1", "page": 2, "excerpt": excerpt}]
    return _call(
        "draft_decision",
        {
            "outcome": outcome,
            "confidence": confidence,
            "criteria": [{"criterion": "prior PT failed", "met": met, "evidence": evidence}],
            "summary": "assessment",
        },
    )


async def _run(llm: FakeLLM, *, passages: list[PolicyPassage] | None = None, **kw: Any) -> Any:
    return await run_case(
        llm=llm, ctx=ctx(passages), patient_ref="patient-001", policy_id="policy-1", **kw
    )


async def test_happy_path_decided() -> None:
    llm = FakeLLM([_search(), _decision("approve", "high", True, REAL_EXCERPT)])
    result = await _run(llm, passages=[PASSAGE])
    assert result.state == "decided"
    assert result.packet is not None
    assert result.packet.outcome == "approve"
    assert result.packet.criteria[0].evidence[0].doc_id == "policy-1"


async def test_fabricated_citation_is_discarded_and_escalates() -> None:
    llm = FakeLLM(
        [_search(), _decision("approve", "high", True, "a fabricated line not retrieved")]
    )
    result = await _run(llm, passages=[PASSAGE])
    assert result.state == "needs_human"
    assert result.packet is not None
    verdict = result.packet.criteria[0]
    assert verdict.met is None  # unsupported determination downgraded
    assert verdict.evidence == []


async def test_denial_escalates() -> None:
    llm = FakeLLM([_search(), _decision("deny", "high", False, REAL_EXCERPT)])
    result = await _run(llm, passages=[PASSAGE])
    assert result.state == "needs_human"


async def test_low_confidence_escalates() -> None:
    llm = FakeLLM([_search(), _decision("approve", "low", True, REAL_EXCERPT)])
    result = await _run(llm, passages=[PASSAGE])
    assert result.state == "needs_human"


async def test_request_info_outcome() -> None:
    llm = FakeLLM([_search(), _decision("request_info", "low", None, None)])
    result = await _run(llm, passages=[PASSAGE])
    assert result.state == "request_info"


async def test_max_steps_escalates() -> None:
    llm = FakeLLM([_search(), _search(), _search()])
    result = await _run(llm, passages=[PASSAGE], limits=HarnessLimits(max_steps=3))
    assert result.state == "needs_human"
    assert "max steps" in result.reason


async def test_token_budget_escalates() -> None:
    llm = FakeLLM(
        [
            _call(
                "search_policy", {"query": "q", "policy_id": "p", "top_k": 5}, in_tok=40, out_tok=20
            )
        ]
    )
    result = await _run(llm, limits=HarnessLimits(token_budget=50))
    assert result.state == "needs_human"
    assert "token budget" in result.reason


async def test_timeout_escalates() -> None:
    clock_values = iter([0.0, 999.0])
    llm = FakeLLM([_search(), _decision("approve", "high", True, REAL_EXCERPT)])
    result = await _run(
        llm,
        passages=[PASSAGE],
        limits=HarnessLimits(timeout_s=10.0),
        clock=lambda: next(clock_values),
    )
    assert result.state == "needs_human"
    assert "timeout" in result.reason


async def test_schema_retry_then_success() -> None:
    # first draft is invalid (determination with no evidence), second is valid
    bad = _decision("approve", "high", True, None)
    good = _decision("approve", "high", True, REAL_EXCERPT)
    llm = FakeLLM([_search(), bad, good])
    result = await _run(llm, passages=[PASSAGE])
    assert result.state == "decided"


async def test_schema_retry_exhausted_escalates() -> None:
    bad = _decision("approve", "high", True, None)
    llm = FakeLLM([_search(), bad, bad])
    result = await _run(llm, passages=[PASSAGE], limits=HarnessLimits(max_schema_retries=1))
    assert result.state == "needs_human"
    assert "schema validation" in result.reason
