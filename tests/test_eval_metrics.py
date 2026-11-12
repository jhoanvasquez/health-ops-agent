"""Unit tests for the eval metrics — pure, hand-built packets, no model."""

from __future__ import annotations

from app.agent.harness import HarnessResult, TerminalState
from app.agent.outputs import Citation, CriterionVerdict, DecisionPacket, Outcome
from app.agent.tools.ports import PolicyPassage
from app.llm.types import Usage
from evals.dataset import ExpectedCriterion, ExpectedResult
from evals.metrics import aggregate, score_case

POOL = [
    PolicyPassage(
        passage="MRI requires a prior failed course of PT.", page=1, doc_id="p1", score=1.0
    )
]
SUPPORTED = Citation(doc_id="p1", page=1, excerpt="MRI requires a prior failed course of PT.")
FABRICATED = Citation(doc_id="p1", page=1, excerpt="no waiting period is ever required")


def _packet(outcome: Outcome, criteria: list[CriterionVerdict]) -> DecisionPacket:
    return DecisionPacket(outcome=outcome, confidence="high", criteria=criteria, summary="s")


def _result(state: TerminalState, packet: DecisionPacket | None) -> HarnessResult:
    return HarnessResult(state=state, packet=packet, reason="", steps=[], usage=Usage())


def _expected(
    outcome: Outcome, state: TerminalState, criteria: list[ExpectedCriterion]
) -> ExpectedResult:
    return ExpectedResult(outcome=outcome, state=state, criteria=criteria)


def test_decision_hit_and_miss() -> None:
    packet = _packet(
        "approve", [CriterionVerdict(criterion="prior PT", met=True, evidence=[SUPPORTED])]
    )
    result = _result("decided", packet)
    assert score_case(
        expected=_expected("approve", "decided", []), result=result, pool=POOL
    ).decision_correct
    assert not score_case(
        expected=_expected("deny", "needs_human", []), result=result, pool=POOL
    ).decision_correct


def test_escalation_accuracy() -> None:
    packet = _packet(
        "deny", [CriterionVerdict(criterion="prior PT", met=False, evidence=[SUPPORTED])]
    )
    result = _result("needs_human", packet)
    assert score_case(
        expected=_expected("deny", "needs_human", []), result=result, pool=POOL
    ).escalation_correct
    # expected a human but the agent decided -> escalation miss
    decided = _result("decided", packet)
    assert not score_case(
        expected=_expected("deny", "needs_human", []), result=decided, pool=POOL
    ).escalation_correct


def test_citation_faithfulness_all_supported() -> None:
    packet = _packet(
        "approve", [CriterionVerdict(criterion="prior PT", met=True, evidence=[SUPPORTED])]
    )
    score = score_case(
        expected=_expected("approve", "decided", []), result=_result("decided", packet), pool=POOL
    )
    assert score.faithfulness == 1.0
    assert score.unsupported == 0


def test_fabricated_citation_is_detected() -> None:
    # a leaked unsupported citation lowers faithfulness and is counted unsupported
    packet = _packet(
        "approve", [CriterionVerdict(criterion="prior PT", met=True, evidence=[FABRICATED])]
    )
    score = score_case(
        expected=_expected("approve", "decided", []), result=_result("decided", packet), pool=POOL
    )
    assert score.cited == 1
    assert score.cited_supported == 0
    assert score.faithfulness == 0.0
    assert score.unsupported == 1


def test_per_criterion_accuracy() -> None:
    packet = _packet(
        "approve",
        [
            CriterionVerdict(
                criterion="member failed physical therapy", met=True, evidence=[SUPPORTED]
            )
        ],
    )
    expected_hit = _expected(
        "approve", "decided", [ExpectedCriterion(contains="physical therapy", met=True)]
    )
    expected_miss = _expected(
        "approve", "decided", [ExpectedCriterion(contains="physical therapy", met=False)]
    )
    assert (
        score_case(
            expected=expected_hit, result=_result("decided", packet), pool=POOL
        ).criteria_correct
        == 1
    )
    assert (
        score_case(
            expected=expected_miss, result=_result("decided", packet), pool=POOL
        ).criteria_correct
        == 0
    )


def test_missing_packet_is_a_decision_miss() -> None:
    result = _result("needs_human", None)
    score = score_case(expected=_expected("approve", "decided", []), result=result, pool=POOL)
    assert not score.decision_correct


def test_aggregate_rates() -> None:
    good = _packet(
        "approve", [CriterionVerdict(criterion="prior PT", met=True, evidence=[SUPPORTED])]
    )
    scores = [
        score_case(
            expected=_expected("approve", "decided", []), result=_result("decided", good), pool=POOL
        ),
        score_case(
            expected=_expected("deny", "needs_human", []),
            result=_result("decided", good),
            pool=POOL,
        ),
    ]
    metrics = aggregate(scores)
    assert metrics.n == 2
    assert metrics.decision_accuracy == 0.5  # one approve-hit, one deny-miss
    assert metrics.citation_faithfulness == 1.0
    assert metrics.unsupported_claims == 0


def test_aggregate_empty() -> None:
    metrics = aggregate([])
    assert metrics.n == 0
    assert metrics.per_criterion_accuracy == 1.0
