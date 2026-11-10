"""Anthropic adapter for `LLMClient`.

Translates the provider-agnostic domain types (`app.llm.types`) to and from the
Anthropic Messages API. The harness never sees an Anthropic SDK type.
"""

from __future__ import annotations

from typing import Any

from anthropic import AsyncAnthropic

from app.config import settings
from app.llm.types import LLMResponse, Message, ToolCall, ToolSpec, Usage


class AnthropicClient:
    """Concrete `LLMClient` backed by the Anthropic Messages API."""

    def __init__(self, *, model: str | None = None, api_key: str | None = None) -> None:
        self._model = model or settings.llm_model
        self._client = AsyncAnthropic(api_key=api_key or settings.anthropic_api_key)

    async def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolSpec],
        max_tokens: int,
    ) -> LLMResponse:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=_to_anthropic_messages(messages),
            tools=[_to_anthropic_tool(t) for t in tools],
        )
        return _from_anthropic_response(response)


def _to_anthropic_tool(tool: ToolSpec) -> dict[str, Any]:
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.input_schema,
    }


def _to_anthropic_messages(messages: list[Message]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for message in messages:
        content: list[dict[str, Any]] = []
        if message.text:
            content.append({"type": "text", "text": message.text})
        for call in message.tool_calls:
            content.append(
                {
                    "type": "tool_use",
                    "id": call.id,
                    "name": call.name,
                    "input": call.arguments,
                }
            )
        for result in message.tool_results:
            content.append(
                {
                    "type": "tool_result",
                    "tool_use_id": result.tool_call_id,
                    "content": result.content,
                    "is_error": result.is_error,
                }
            )
        out.append({"role": message.role, "content": content})
    return out


def _from_anthropic_response(response: Any) -> LLMResponse:
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append(
                ToolCall(id=block.id, name=block.name, arguments=dict(block.input))
            )
    return LLMResponse(
        text="".join(text_parts),
        tool_calls=tool_calls,
        usage=Usage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        ),
        stop_reason=response.stop_reason or "",
    )
