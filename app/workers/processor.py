"""Core case processing — infrastructure-free, so it unit-tests with fakes.

Loads a case, runs the agent harness, and persists the terminal state, the
decision packet, and one audit entry per agent step. The RabbitMQ consumer
(`case_worker.py`) is the only part that touches the broker.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.harness import DEFAULT_LIMITS, HarnessLimits, HarnessResult, run_case
from app.agent.tools.base import ToolContext
from app.db.models import AuditEntry, Case, CaseState
from app.llm.client import LLMClient


class CaseNotFoundError(Exception):
    """Raised when a queued case id has no matching row."""


async def process_case(
    *,
    case_id: UUID,
    session: AsyncSession,
    llm: LLMClient,
    ctx: ToolContext,
    limits: HarnessLimits = DEFAULT_LIMITS,
) -> HarnessResult:
    case = await session.get(Case, case_id)
    if case is None:
        raise CaseNotFoundError(str(case_id))

    case.state = CaseState.processing
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
