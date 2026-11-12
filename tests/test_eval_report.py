"""Tests for the Markdown eval report rendering (pure)."""

from __future__ import annotations

from app.agent.harness import HarnessResult
from app.llm.types import Usage
from evals.dataset import CasePassage, EvalCase, ExpectedResult
from evals.metrics import CaseScore, Metrics
from evals.report import render_report
from evals.runner import CaseResult

PERFECT = Metrics(
    n=2,
    decision_accuracy=1.0,
    escalation_accuracy=1.0,
    citation_faithfulness=1.0,
    unsupported_claims=0,
    per_criterion_accuracy=1.0,
)


def _case(case_id: str) -> EvalCase:
    return EvalCase(
        id=case_id,
        tags=["deny"],
        policy_id="p",
        patient={},
        policy_passages=[CasePassage(doc_id="d", page=1, passage="x")],
        expected=ExpectedResult(outcome="approve", state="decided", criteria=[]),
    )


def test_report_no_misses() -> None:
    md = render_report([], PERFECT, "claude-haiku-4-5")
    assert "No misses on this run." in md
    assert "`claude-haiku-4-5`" in md
    assert "| Decision accuracy | 1.000 |" in md


def test_report_lists_a_decision_miss() -> None:
    score = CaseScore(
        decision_correct=False,
        escalation_correct=True,
        cited=0,
        cited_supported=0,
        criteria_total=0,
        criteria_correct=0,
    )
    result = HarnessResult(state="decided", packet=None, reason="", steps=[], usage=Usage())
    case_result = CaseResult(case=_case("bad-case"), result=result, score=score)
    metrics = Metrics(1, 0.0, 1.0, 1.0, 0, 1.0)

    md = render_report([case_result], metrics, "m")
    assert "bad-case" in md
    assert "decision" in md
    assert "expected: outcome `approve`" in md
