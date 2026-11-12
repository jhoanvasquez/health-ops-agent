"""Eval case dataset: a versioned, self-contained set of synthetic cases.

Each case carries everything needed to run it — the patient, the policy passages
`search_policy` should return, and the expected result — so the harness runs with
no database and no embedding API. See `design.md` (change `evaluation-system`).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from app.agent.harness import TerminalState
from app.agent.outputs import Outcome

CASES_DIR = Path(__file__).parent / "cases"


class CasePassage(BaseModel):
    """A policy passage the fixture store returns for this case (a retrieval stand-in)."""

    doc_id: str
    page: int
    passage: str


class ExpectedCriterion(BaseModel):
    """An expected per-criterion verdict, matched to the agent's free text by substring."""

    contains: str
    met: bool | None


class ExpectedResult(BaseModel):
    outcome: Outcome
    state: TerminalState
    criteria: list[ExpectedCriterion] = []


class EvalCase(BaseModel):
    id: str
    tags: list[str] = []
    hidden: bool = False
    policy_id: str
    patient: dict[str, Any]
    policy_passages: list[CasePassage]
    expected: ExpectedResult


def load_cases(*, include_hidden: bool = False, cases_dir: Path = CASES_DIR) -> list[EvalCase]:
    """Load and validate every case JSON. Raises on a malformed file — never skips silently."""
    cases: list[EvalCase] = []
    for path in sorted(cases_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            case = EvalCase.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(f"invalid eval case {path.name}: {exc}") from exc
        if case.hidden and not include_hidden:
            continue
        cases.append(case)
    return cases
