"""Tests for the structured agent outputs and their citation guardrail."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.agent.outputs import Citation, CriterionVerdict, DecisionPacket

CITATION = Citation(doc_id="policy-123", page=4, excerpt="Prior imaging is required.")


def test_determination_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        CriterionVerdict(criterion="Prior imaging performed", met=True, evidence=[])


def test_cannot_determine_allows_no_evidence() -> None:
    verdict = CriterionVerdict(criterion="Prior imaging performed", met=None)
    assert verdict.evidence == []


def test_met_with_evidence_is_valid() -> None:
    verdict = CriterionVerdict(criterion="Prior imaging performed", met=True, evidence=[CITATION])
    assert verdict.evidence[0].doc_id == "policy-123"


def test_needs_human_on_denial() -> None:
    packet = DecisionPacket(
        outcome="deny",
        confidence="high",
        criteria=[CriterionVerdict(criterion="X", met=False, evidence=[CITATION])],
        summary="Criterion not met.",
    )
    assert packet.needs_human is True


def test_needs_human_on_low_confidence() -> None:
    packet = DecisionPacket(
        outcome="approve",
        confidence="low",
        criteria=[CriterionVerdict(criterion="X", met=True, evidence=[CITATION])],
        summary="Likely met but uncertain.",
    )
    assert packet.needs_human is True


def test_confident_approval_does_not_escalate() -> None:
    packet = DecisionPacket(
        outcome="approve",
        confidence="high",
        criteria=[CriterionVerdict(criterion="X", met=True, evidence=[CITATION])],
        summary="All criteria met.",
    )
    assert packet.needs_human is False
