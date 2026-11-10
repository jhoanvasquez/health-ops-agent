"""Guardrails enforced in code, not in prompts (design D5).

The citation guardrail is the project's core safety property: every claim the
agent makes must be grounded in evidence it actually retrieved. We cross-check
each citation against the passages `search_policy` returned for THIS case, drop
fabricated ones, and downgrade any determination that no longer has support to
"cannot determine" — which the harness then routes to a human / request_info.
"""

from __future__ import annotations

from app.agent.outputs import Citation, CriterionVerdict, DecisionPacket
from app.agent.tools.ports import PolicyPassage


def _normalize(text: str) -> str:
    return " ".join(text.split()).lower()


def citation_supported(citation: Citation, pool: list[PolicyPassage]) -> bool:
    """True if the citation's excerpt is a verbatim part of a retrieved passage."""
    needle = _normalize(citation.excerpt)
    if not needle:
        return False
    return any(
        passage.doc_id == citation.doc_id and needle in _normalize(passage.passage)
        for passage in pool
    )


def verify_citations(packet: DecisionPacket, pool: list[PolicyPassage]) -> DecisionPacket:
    """Return a packet with fabricated citations removed.

    A determination (`met` is true/false) that loses all of its support becomes
    `met = None` (cannot determine) with no evidence.
    """
    verified: list[CriterionVerdict] = []
    for verdict in packet.criteria:
        supported = [c for c in verdict.evidence if citation_supported(c, pool)]
        if verdict.met is not None and not supported:
            verified.append(CriterionVerdict(criterion=verdict.criterion, met=None, evidence=[]))
        else:
            verified.append(
                CriterionVerdict(criterion=verdict.criterion, met=verdict.met, evidence=supported)
            )
    return DecisionPacket(
        outcome=packet.outcome,
        confidence=packet.confidence,
        criteria=verified,
        summary=packet.summary,
    )
