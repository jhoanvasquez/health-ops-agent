"""Core case processing — infrastructure-free, so it unit-tests with fakes.

Loads a case, runs the agent harness, and persists the terminal state, the
decision packet, and one audit entry per agent step. Reprocessing a terminal case
is a no-op, so retries and duplicate deliveries are safe. The RabbitMQ consumer
(`case_worker.py`) is the only part that touches the broker.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.harness import DEFAULT_LIMITS, HarnessLimits, HarnessResult, run_case
from app.agent.tools.base import ToolContext
from app.db.models import TERMINAL_STATES, AuditEntry, Case, CaseState
from app.llm.client import LLMClient

_ERROR_MAX_CHARS = 200


class CaseNotFoundError(Exception):
    """Raised when a queued case id has no matching row."""


def redact_error(exc: BaseException) -> str:
    """A short, redacted error summary safe to persist — type plus a truncated message."""
    return f"{type(exc).__name__}: {str(exc)[:_ERROR_MAX_CHARS]}"


async def process_case(
    *,
    case_id: UUID,
    session: AsyncSession,
    llm: LLMClient,
    ctx: ToolContext,
    limits: HarnessLimits = DEFAULT_LIMITS,
    attempt: int = 1,
) -> HarnessResult | None:
    """Process a case. Returns None (a no-op) if the case is already terminal."""
    case = await session.get(Case, case_id)
    if case is None:
        raise CaseNotFoundError(str(case_id))
    if case.state in TERMINAL_STATES:
        return None  # already decided/failed — reprocessing must not run the agent again

    case.state = CaseState.processing
    case.attempts = attempt
    await session.flush()

    result = await run_case(
        llm=llm,
        ctx=ctx,
        patient_ref=case.patient_ref,
        policy_id=case.policy_id,
        limits=limits,
    )

    case.state = CaseState(result.state)
    case.packet = result.packet.model_dump(mode="json") if result.packet is not None else None
    for entry in result.steps:
        session.add(
            AuditEntry(
                case_id=case.id,
                step=entry.step,
                tool=entry.tool,
                input_redacted=entry.input_redacted,
                output_redacted=entry.output_redacted,
            )
        )
    await session.commit()
    return result


async def mark_failed(*, session: AsyncSession, case_id: UUID, attempt: int, error: str) -> None:
    """Record a dead-lettered case as failed with its attempt count and redacted error.

    Uses a fresh session (the processing session was rolled back on the failure).
    """
    case = await session.get(Case, case_id)
    if case is None:
        return
    case.state = CaseState.failed
    case.attempts = attempt
    case.last_error = error
    await session.commit()
