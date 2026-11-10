"""Structured agent outputs (design D3).

These are the schemas the agent's final decision is validated against. The
citation guardrail is enforced here at the type level: a criterion that reaches
a determination (`met is not None`) MUST cite evidence. A verdict without
evidence cannot be constructed — the harness discards uncited claims before
assembling the packet, and this is the last line of defense.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator

Outcome = Literal["approve", "deny", "request_info"]
Confidence = Literal["high", "low"]


class Citation(BaseModel):
    """Evidence supporting a claim: a document, the page, and the exact excerpt."""

    doc_id: str
    page: int
    excerpt: str


class CriterionVerdict(BaseModel):
    """The agent's judgment on a single policy criterion.

    `met is None` means "cannot determine" — it drives a `request_info` outcome
    and is the only case allowed to carry no evidence.
    """

    criterion: str
    met: bool | None
    evidence: list[Citation] = []

    @model_validator(mode="after")
    def _require_evidence_for_determination(self) -> CriterionVerdict:
        if self.met is not None and not self.evidence:
            raise ValueError(
                f"criterion {self.criterion!r} has a determination (met={self.met}) "
                "but cites no evidence; every determination must be supported."
            )
        return self


class DecisionPacket(BaseModel):
    """The agent's drafted decision for a prior-authorization case."""

    outcome: Outcome
    confidence: Confidence
    criteria: list[CriterionVerdict]
    summary: str

    @property
    def needs_human(self) -> bool:
        """Escalation rule (design D4): denials and low confidence need a human."""
        return self.outcome == "deny" or self.confidence == "low"
