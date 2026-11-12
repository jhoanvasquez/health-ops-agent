"""Runner tests: the self-check pipeline reproduces expected metrics, no network."""

from __future__ import annotations

from app.agent.harness import TerminalState
from app.agent.outputs import Outcome
from evals.dataset import CasePassage, EvalCase, ExpectedCriterion, ExpectedResult
from evals.metrics import aggregate
from evals.runner import replay_llm_factory, run_dataset

PASSAGE = CasePassage(doc_id="p1", page=1, passage="MRI requires a prior failed course of PT.")


def _case(
    case_id: str,
    outcome: Outcome,
    state: TerminalState,
    met: bool | None,
    tags: list[str] | None = None,
) -> EvalCase:
    return EvalCase(
        id=case_id,
        tags=tags or [],
        policy_id="pol",
        patient={"resourceType": "Bundle", "id": case_id},
        policy_passages=[PASSAGE],
        expected=ExpectedResult(
            outcome=outcome,
            state=state,
            criteria=[ExpectedCriterion(contains="PT", met=met)],
        ),
    )


async def test_self_check_reproduces_perfect_metrics() -> None:
    cases = [
        _case("approve", "approve", "decided", met=True),
        _case("deny", "deny", "needs_human", met=False),
        _case("low-confidence", "approve", "needs_human", met=True),
        _case("request-info", "request_info", "request_info", met=None),
        _case("trap", "approve", "needs_human", met=None, tags=["fabricated-citation"]),
    ]
    results = await run_dataset(cases, replay_llm_factory())
    metrics = aggregate([r.score for r in results])

    assert metrics.n == 5
    assert metrics.decision_accuracy == 1.0
    assert metrics.escalation_accuracy == 1.0
    assert metrics.citation_faithfulness == 1.0
    assert metrics.per_criterion_accuracy == 1.0
    assert metrics.unsupported_claims == 0


async def test_trap_case_escalates_and_strips_fabricated_citation() -> None:
    [result] = await run_dataset(
        [_case("trap", "approve", "needs_human", met=None, tags=["fabricated-citation"])],
        replay_llm_factory(),
    )
    # the guardrail downgraded the fabricated determination and escalated
    assert result.result.state == "needs_human"
    assert result.result.packet is not None
    verdict = result.result.packet.criteria[0]
    assert verdict.met is None
    assert verdict.evidence == []
