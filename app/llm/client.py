"""The `LLMClient` interface the harness depends on.

Keeping this a Protocol (structural typing) means the harness never imports a
concrete provider. Adapters live beside it (`anthropic.py`); tests supply a fake.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.llm.types import LLMResponse, Message, ToolSpec


@runtime_checkable
class LLMClient(Protocol):
    """A chat-completion client with tool use."""

    async def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolSpec],
        max_tokens: int,
    ) -> LLMResponse:
        """Run one completion.

        Returns the model's text, any tool calls it requested, token usage, and
        the stop reason. Implementations must not mutate `messages`.
        """
        ...
