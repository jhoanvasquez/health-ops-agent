"""Processor tests — HarnessResult is mapped onto the Case and audit log."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.agent.tools.base import ToolContext
from app.agent.tools.ports import PolicyPassage
from app.db.models import AuditEntry, Case, CaseState
from app.llm.types import LLMResponse, Message, ToolCall, ToolSpec, Usage
from app.workers.processor import mark_failed, process_case, redact_error

PASSAGE = PolicyPassage(passage="MRI requires prior PT.", page=2, doc_id="policy-1", score=0.9)


class FakeLLM:
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
        return [0.0, 0.1]


class FakeStore:
    async def search(
        self, *, policy_id: str, embedding: list[float], top_k: int
    ) -> list[PolicyPassage]:
        return [PASSAGE]


class FakeSession:
    def __init__(self, case: Case) -> None:
        self._case = case
        self.added: list[Any] = []
        self.committed = False

    async def get(self, model: Any, ident: Any) -> Any:
        return self._case

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        self.committed = True


def _call(name: str, args: dict[str, Any]) -> LLMResponse:
    return LLMResponse(
        tool_calls=[ToolCall(id=f"c-{name}", name=name, arguments=args)],
        usage=Usage(input_tokens=5, output_tokens=5),
        stop_reason="tool_use",
    )


async def test_process_case_persists_decision_and_audit() -> None:
    case = Case(
        id=uuid4(),
        idempotency_key="k",
        policy_id="policy-1",
        patient_ref="patient-001",
        state=CaseState.received,
    )
    session = FakeSession(case)
    llm = FakeLLM(
        [
            _call("search_policy", {"query": "MRI", "policy_id": "policy-1", "top_k": 5}),
            _call(
                "draft_decision",
                {
                    "outcome": "approve",
                    "confidence": "high",
                    "criteria": [
                        {
                            "criterion": "prior PT",
                            "met": True,
                            "evidence": [
                                {
                                    "doc_id": "policy-1",
                                    "page": 2,
                                    "excerpt": "MRI requires prior PT.",
                                }
                            ],
                        }
                    ],
                    "summary": "met",
                },
            ),
        ]
    )
    ctx = ToolContext(FakePatients(), FakeStore(), FakeEmbedder())

    result = await process_case(case_id=case.id, session=session, llm=llm, ctx=ctx)  # type: ignore[arg-type]

    assert result.state == "decided"
    assert case.state == CaseState.decided
    assert case.packet is not None
    assert case.packet["outcome"] == "approve"
    assert session.committed
    assert any(isinstance(obj, AuditEntry) for obj in session.added)


async def test_terminal_case_is_skipped() -> None:
    case = Case(
        id=uuid4(),
        idempotency_key="k",
        policy_id="p",
        patient_ref="pt",
        state=CaseState.decided,
    )
    session = FakeSession(case)
    llm = FakeLLM([])  # must never be called
    ctx = ToolContext(FakePatients(), FakeStore(), FakeEmbedder())

    result = await process_case(case_id=case.id, session=session, llm=llm, ctx=ctx)  # type: ignore[arg-type]

    assert result is None
    assert llm.calls == 0
    assert not session.committed
    assert session.added == []


async def test_mark_failed_records_failure() -> None:
    case = Case(
        id=uuid4(),
        idempotency_key="k",
        policy_id="p",
        patient_ref="pt",
        state=CaseState.processing,
    )
    session = FakeSession(case)

    await mark_failed(session=session, case_id=case.id, attempt=3, error="ValueError: boom")  # type: ignore[arg-type]

    assert case.state == CaseState.failed
    assert case.attempts == 3
    assert case.last_error == "ValueError: boom"
    assert session.committed


def test_redact_error_truncates() -> None:
    redacted = redact_error(ValueError("x" * 500))
    assert redacted.startswith("ValueError: ")
    assert len(redacted) <= len("ValueError: ") + 200
