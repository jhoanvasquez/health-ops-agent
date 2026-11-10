"""Tool base class, context, error type, and the central invoke helper.

A tool is stateless: it declares a name, a description (the interface the model
reads — see `.claude/rules/tools-and-skills.md`), and a Pydantic input model.
All runtime dependencies arrive through `ToolContext` at call time, so tools can
be instantiated without infrastructure.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from app.agent.tools.ports import Embedder, PatientRepository, PolicyStore
from app.llm.types import ToolSpec

PayloadT = TypeVar("PayloadT", bound=BaseModel)


@dataclass
class ToolContext:
    """Runtime dependencies passed to a tool's `run`."""

    patients: PatientRepository
    policy_store: PolicyStore
    embedder: Embedder


class ToolError(BaseModel):
    """A structured failure returned to the model instead of a raised exception."""

    error: str
    retryable: bool = False


class Tool(ABC, Generic[PayloadT]):
    """A deterministic, testable function the model may call by name."""

    name: str
    description: str
    input_model: type[PayloadT]

    def spec(self) -> ToolSpec:
        """The schema advertised to the model."""
        return ToolSpec(
            name=self.name,
            description=self.description,
            input_schema=self.input_model.model_json_schema(),
        )

    @abstractmethod
    async def run(self, payload: PayloadT, ctx: ToolContext) -> Any:
        """Execute the tool with validated input. Return data or a `ToolError`."""
        ...


async def invoke(tool: Tool[Any], arguments: dict[str, Any], ctx: ToolContext) -> Any:
    """Validate raw arguments against the tool's schema, then run it.

    Invalid input never raises to the caller: it becomes a non-retryable
    `ToolError` handed back to the model (REQ-5).
    """
    try:
        payload = tool.input_model.model_validate(arguments)
    except ValidationError as exc:
        return ToolError(error=f"invalid input for {tool.name}: {exc.errors()}", retryable=False)
    return await tool.run(payload, ctx)
