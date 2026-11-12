"""Deterministic eval metrics — pure functions, no I/O, no model.

Compares the agent's structured `HarnessResult` against a case's expected answer.
Citation faithfulness reuses `app.agent.guardrails.citation_supported`, so the
eval measures the exact rule the harness enforces — end to end.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.guardrails import citation_supported
from app.agent.harness import HarnessResult
from app.agent.outputs import CriterionVerdict, DecisionPacket
from app.agent.tools.ports import PolicyPassage
from evals.dataset import ExpectedResult


@dataclass
class CaseScore:
    """Per-case comparison of actual vs expected."""

    decision_correct: bool
    escalation_correct: bool
    cited: int  # citations in the final packet
    cited_supported: int  # of those, how many are grounded in the passages
    criteria_total: int  # expected criteria
    criteria_correct: int  # matched with the correct `met`

    @property
    def faithfulness(self) -> float:
        """Share of cited evidence grounded in the retrieved passages (1.0 if none cited)."""
        return 1.0 if self.cited == 0 else self.cited_supported / self.cited

    @property
    def unsupported(self) -> int:
        """Citations that slipped through without support (should be 0 — a guardrail check)."""
        return self.cited - self.cited_supported


@dataclass
class Metrics:
    """Dataset-level aggregate."""

    n: int
    decision_accuracy: float
    escalation_accuracy: float
    citation_faithfulness: float
    unsupported_claims: int
    per_criterion_accuracy: float


def _find_criterion(packet: DecisionPacket, contains: str) -> CriterionVerdict | None:
    needle = contains.lower()
    return next((v for v in packet.criteria if needle in v.criterion.lower()), None)


def score_case(
    *, expected: ExpectedResult, result: HarnessResult, pool: list[PolicyPassage]
) -> CaseScore:
    """Score one case. `pool` is the passages the agent was given for this case."""
    packet = result.packet

    decision_correct = packet is not None and packet.outcome == expected.outcome
    escalation_correct = (result.state == "needs_human") == (expected.state == "needs_human")

    cited = 0
    cited_supported = 0
    criteria_correct = 0
    if packet is not None:
        for verdict in packet.criteria:
            for citation in verdict.evidence:
                cited += 1
                if citation_supported(citation, pool):
                    cited_supported += 1
        for expected_criterion in expected.criteria:
            match = _find_criterion(packet, expected_criterion.contains)
            if match is not None and match.met == expected_criterion.met:
                criteria_correct += 1

    return CaseScore(
        decision_correct=decision_correct,
        escalation_correct=escalation_correct,
        cited=cited,
        cited_supported=cited_supported,
        criteria_total=len(expected.criteria),
        criteria_correct=criteria_correct,
    )


def aggregate(scores: list[CaseScore]) -> Metrics:
    """Aggregate per-case scores into dataset-level rates."""
    n = len(scores)
    if n == 0:
        return Metrics(0, 0.0, 0.0, 1.0, 0, 1.0)

    criteria_total = sum(s.criteria_total for s in scores)
    criteria_correct = sum(s.criteria_correct for s in scores)

    return Metrics(
        n=n,
        decision_accuracy=sum(s.decision_correct for s in scores) / n,
        escalation_accuracy=sum(s.escalation_correct for s in scores) / n,
        citation_faithfulness=sum(s.faithfulness for s in scores) / n,
        unsupported_claims=sum(s.unsupported for s in scores),
        per_criterion_accuracy=(criteria_correct / criteria_total if criteria_total else 1.0),
    )
