"""Provider-agnostic domain types for the LLM layer.

The agent harness speaks only these types. Each provider adapter translates to
and from its own SDK, so swapping providers (for model comparison in evals)
never touches the harness.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["user", "assistant"]


class ToolSpec(BaseModel):
    """A tool offered to the model. `input_schema` is a JSON Schema object."""

    name: str
    description: str
    input_schema: dict[str, Any]


class ToolCall(BaseModel):
    """A tool invocation the model requested."""

    id: str
    name: str
    arguments: dict[str, Any]


class ToolResult(BaseModel):
    """The result of running a tool, fed back to the model."""

    tool_call_id: str
    content: str
    is_error: bool = False


class Message(BaseModel):
    """One turn in the conversation.

    A user turn carries `text` and/or `tool_results`; an assistant turn carries
    `text` and/or `tool_calls`.
    """

    role: Role
    text: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)


class Usage(BaseModel):
    """Token accounting for one completion."""

    input_tokens: int = 0
    output_tokens: int = 0


class LLMResponse(BaseModel):
    """A single model completion."""

    text: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    stop_reason: str = ""
