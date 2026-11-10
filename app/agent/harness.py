"""The agent harness: a bounded tool-use loop with guardrails (ADR 002).

model -> tool call -> result -> model, until the model submits `draft_decision`
or a limit (steps / timeout / token budget) forces escalation to a human. The
harness is independent of the database and the LLM provider — it speaks the
`LLMClient` protocol and returns an in-memory result the worker persists.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from app.agent.guardrails import verify_citations
from app.agent.outputs import DecisionPacket
from app.agent.prompts import load_prompt
from app.agent.tools.base import ToolContext, ToolError, invoke
from app.agent.tools.ports import PolicyPassage
from app.agent.tools.registry import BY_NAME, REGISTRY
from app.llm.client import LLMClient
from app.llm.types import Message, ToolResult, Usage

DRAFT_DECISION = "draft_decision"
TerminalState = Literal["decided", "needs_human", "request_info"]


@dataclass(frozen=True)
class HarnessLimits:
    """Hard bounds on a single case run. Breaching any escalates to a human."""

    max_steps: int = 12
    timeout_s: float = 120.0
    token_budget: int = 200_000
    max_output_tokens: int = 4096
    max_schema_retries: int = 1


DEFAULT_LIMITS = HarnessLimits()


class AuditStep(BaseModel):
    """One recorded tool execution, with sensitive data redacted."""

    step: int
    tool: str
    input_redacted: dict[str, Any]
    output_redacted: dict[str, Any]


@dataclass
class HarnessResult:
    state: TerminalState
    packet: DecisionPacket | None
    reason: str
    steps: list[AuditStep]
    usage: Usage


def _initial_prompt(patient_ref: str, policy_id: str) -> str:
    return (
        f"Evaluate the prior-authorization case for patient '{patient_ref}' against "
        f"policy '{policy_id}'. Gather the patient data and the relevant policy "
        "criteria, then submit your decision with draft_decision."
    )


def _redact(tool: str, value: Any) -> dict[str, Any]:
    """Redact tool output for the audit log — never store raw PHI."""
    if isinstance(value, ToolError):
        return {"error": value.error, "retryable": value.retryable}
    if tool == "get_patient" and isinstance(value, dict):
        return {"resourceType": value.get("resourceType"), "redacted": True}
    if isinstance(value, list):
        return {"count": len(value)}
    if isinstance(value, dict):
        return {"keys": sorted(value)[:10]}
    return {"value": str(value)[:200]}


def _result_to_content(result: Any) -> tuple[str, bool]:
    """Serialize a tool result for the model, and whether it is an error."""
    if isinstance(result, ToolError):
        return result.model_dump_json(), True
    if isinstance(result, BaseModel):
        return result.model_dump_json(), False
    if isinstance(result, list):
        payload = [r.model_dump() if isinstance(r, BaseModel) else r for r in result]
        return json.dumps(payload), False
    return json.dumps(result), False


def _finalize(
    packet: DecisionPacket, pool: list[PolicyPassage], steps: list[AuditStep], usage: Usage
) -> HarnessResult:
    verified = verify_citations(packet, pool)
    undetermined = any(v.met is None for v in verified.criteria)
    if verified.outcome == "request_info":
        return HarnessResult(
            "request_info", verified, "agent requested more information", steps, usage
        )
    if undetermined:
        return HarnessResult(
            "needs_human", verified, "unsupported determination after citation check", steps, usage
        )
    if verified.needs_human:
        return HarnessResult(
            "needs_human", verified, "denial or low confidence requires human review", steps, usage
        )
    return HarnessResult("decided", verified, "all criteria met and cited", steps, usage)


async def run_case(
    *,
    llm: LLMClient,
    ctx: ToolContext,
    patient_ref: str,
    policy_id: str,
    limits: HarnessLimits = DEFAULT_LIMITS,
    system_prompt: str | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> HarnessResult:
    """Run one prior-authorization case through the agent loop."""
    system = system_prompt if system_prompt is not None else load_prompt("v1", "decide")
    specs = [tool.spec() for tool in REGISTRY]
    messages: list[Message] = [Message(role="user", text=_initial_prompt(patient_ref, policy_id))]
    pool: list[PolicyPassage] = []
    steps: list[AuditStep] = []
    usage = Usage()
    schema_retries = 0
    start = clock()

    for step in range(1, limits.max_steps + 1):
        if clock() - start > limits.timeout_s:
            return HarnessResult("needs_human", None, "timeout exceeded", steps, usage)

        response = await llm.complete(
            system=system, messages=messages, tools=specs, max_tokens=limits.max_output_tokens
        )
        usage = Usage(
            input_tokens=usage.input_tokens + response.usage.input_tokens,
            output_tokens=usage.output_tokens + response.usage.output_tokens,
        )
        if usage.input_tokens + usage.output_tokens > limits.token_budget:
            return HarnessResult("needs_human", None, "token budget exceeded", steps, usage)

        if not response.tool_calls:
            return HarnessResult("needs_human", None, "model returned no tool call", steps, usage)

        messages.append(
            Message(role="assistant", text=response.text, tool_calls=response.tool_calls)
        )

        decision_call = next(
            (call for call in response.tool_calls if call.name == DRAFT_DECISION), None
        )
        if decision_call is not None:
            try:
                packet = DecisionPacket.model_validate(decision_call.arguments)
            except ValidationError as exc:
                schema_retries += 1
                if schema_retries > limits.max_schema_retries:
                    return HarnessResult(
                        "needs_human", None, "repeated schema validation failure", steps, usage
                    )
                messages.append(
                    Message(
                        role="user",
                        tool_results=[
                            ToolResult(
                                tool_call_id=decision_call.id,
                                content=json.dumps({"validation_error": str(exc)}),
                                is_error=True,
                            )
                        ],
                    )
                )
                continue
            return _finalize(packet, pool, steps, usage)

        results: list[ToolResult] = []
        for call in response.tool_calls:
            tool = BY_NAME.get(call.name)
            if tool is None:
                results.append(
                    ToolResult(
                        tool_call_id=call.id,
                        content=json.dumps({"error": f"unknown tool {call.name}"}),
                        is_error=True,
                    )
                )
                continue
            result = await invoke(tool, call.arguments, ctx)
            if call.name == "search_policy" and isinstance(result, list):
                pool.extend(p for p in result if isinstance(p, PolicyPassage))
            steps.append(
                AuditStep(
                    step=step,
                    tool=call.name,
                    input_redacted=dict(call.arguments),
                    output_redacted=_redact(call.name, result),
                )
            )
            content, is_error = _result_to_content(result)
            results.append(ToolResult(tool_call_id=call.id, content=content, is_error=is_error))
        messages.append(Message(role="user", tool_results=results))

    return HarnessResult("needs_human", None, "max steps reached", steps, usage)
