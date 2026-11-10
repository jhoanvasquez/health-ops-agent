"""The tool registry.

The single source of truth for the tools the agent may use. The CI description
check (`scripts/check_descriptions.py`) imports this list and validates every
tool's description. Tools instantiate without arguments (dependencies arrive via
`ToolContext`), so importing this module is side-effect free.
"""

from __future__ import annotations

from typing import Any

from app.agent.tools.base import Tool
from app.agent.tools.get_patient import GetPatientTool
from app.agent.tools.search_policy import SearchPolicyTool

REGISTRY: list[Tool[Any]] = [
    GetPatientTool(),
    SearchPolicyTool(),
]

BY_NAME: dict[str, Tool[Any]] = {tool.name: tool for tool in REGISTRY}
