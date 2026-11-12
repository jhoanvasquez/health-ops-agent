"""Eval runner: run each case through the real agent harness and score it.

Builds a fixture `ToolContext` per case (no DB, no Voyage) and calls the real
`run_case`, so we measure the actual agent — loop, guardrails, escalation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.agent.harness import HarnessResult, run_case
from app.agent.outputs import Outcome
from app.agent.tools.base import ToolContext
from app.agent.tools.ports import PolicyPassage
from app.llm.client import LLMClient
from app.llm.types import LLMResponse, ToolCall, Usage
from evals.dataset import EvalCase, ExpectedCriterion
from evals.fixtures import (
    FixturePatientRepository,
    FixturePolicyStore,
    ReplayLLM,
    StubEmbedder,
)
from evals.metrics import CaseScore, score_case

LLMFactory = Callable[[EvalCase], LLMClient]


@dataclass
class CaseResult:
    case: EvalCase
    result: HarnessResult
    score: CaseScore


def _pool(case: EvalCase) -> list[PolicyPassage]:
    return [
        PolicyPassage(passage=p.passage, page=p.page, doc_id=p.doc_id, score=1.0)
        for p in case.policy_passages
    ]


async def run_one(case: EvalCase, llm: LLMClient) -> CaseResult:
    ctx = ToolContext(
        patients=FixturePatientRepository(case.patient),
        policy_store=FixturePolicyStore(case.policy_passages),
        embedder=StubEmbedder(),
    )
    result = await run_case(llm=llm, ctx=ctx, patient_ref=case.id, policy_id=case.policy_id)
    score = score_case(expected=case.expected, result=result, pool=_pool(case))
    return CaseResult(case=case, result=result, score=score)


async def run_dataset(cases: list[EvalCase], llm_for: LLMFactory) -> list[CaseResult]:
    return [await run_one(case, llm_for(case)) for case in cases]


# ── self-check scripting ────────────────────────────────────────────────────
# A ReplayLLM that "acts out" each case's expected result through the real
# harness. If the pipeline is correct, perfect inputs produce perfect metrics —
# so the self-check gates loader + fixtures + harness routing + metrics.

_FABRICATED_TAG = "fabricated-citation"


def _tool_call(name: str, arguments: dict[str, Any]) -> LLMResponse:
    return LLMResponse(
        tool_calls=[ToolCall(id=f"c-{name}", name=name, arguments=arguments)],
        usage=Usage(input_tokens=1, output_tokens=1),
        stop_reason="tool_use",
    )


def _default_met(outcome: Outcome) -> bool | None:
    return {"approve": True, "deny": False, "request_info": None}[outcome]


def _script_for(case: EvalCase) -> list[LLMResponse]:
    expected = case.expected
    passages = case.policy_passages
    supported = (
        {"doc_id": passages[0].doc_id, "page": passages[0].page, "excerpt": passages[0].passage}
        if passages
        else None
    )
    fabricate = _FABRICATED_TAG in case.tags

    criteria: list[ExpectedCriterion] = expected.criteria or [
        ExpectedCriterion(contains="criterion", met=_default_met(expected.outcome))
    ]
    payload: list[dict[str, Any]] = []
    for index, criterion in enumerate(criteria):
        if fabricate and index == 0:
            # draft a determination on a fabricated citation; the guardrail must strip it
            payload.append(
                {
                    "criterion": criterion.contains,
                    "met": True,
                    "evidence": [
                        {"doc_id": "x", "page": 1, "excerpt": "fabricated unsupported text"}
                    ],
                }
            )
        elif criterion.met is None:
            payload.append({"criterion": criterion.contains, "met": None, "evidence": []})
        else:
            evidence = [supported] if supported is not None else []
            payload.append(
                {"criterion": criterion.contains, "met": criterion.met, "evidence": evidence}
            )

    # Reproduce a low-confidence escalation (needs_human that isn't a denial or a
    # fabricated/undetermined criterion) by drafting low confidence.
    all_determined = all(entry["met"] is not None for entry in payload)
    low_confidence = (
        expected.state == "needs_human"
        and expected.outcome != "deny"
        and not fabricate
        and all_determined
    )

    draft = {
        "outcome": expected.outcome,
        "confidence": "low" if low_confidence else "high",
        "criteria": payload,
        "summary": "self-check",
    }
    return [
        _tool_call(
            "search_policy", {"query": "self-check", "policy_id": case.policy_id, "top_k": 5}
        ),
        _tool_call("draft_decision", draft),
    ]


def replay_llm_factory() -> LLMFactory:
    """An `LLMFactory` that scripts a `ReplayLLM` per case for the self-check."""
    return lambda case: ReplayLLM(_script_for(case))
