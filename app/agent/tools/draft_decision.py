"""`draft_decision` tool — the agent's terminal action.

Its input schema IS the `DecisionPacket` (design D3): the model fills the packet
via tool use, and the harness validates it with Pydantic, cross-checks citations,
and routes the result. The harness intercepts this call as terminal; `run` simply
returns the validated packet for the uniform tool interface.
"""

from __future__ import annotations

from app.agent.outputs import DecisionPacket
from app.agent.tools.base import Tool, ToolContext


class DraftDecisionTool(Tool[DecisionPacket]):
    name = "draft_decision"
    description = (
        "Submit the final prior-authorization decision for the case. "
        "Use when you have evaluated every required criterion and are ready to "
        "conclude. Do NOT use before gathering patient data (use get_patient) and "
        "the policy wording (use search_policy). "
        "Input: outcome (approve|deny|request_info), confidence (high|low), criteria "
        "(each with criterion text, met true/false/null, and evidence citations), and "
        "a summary. "
        "Returns the validated decision packet. Terminal: calling this ends the "
        "agent's work; the system checks citations and escalates denials and "
        "low-confidence cases to a human."
    )
    input_model = DecisionPacket

    async def run(self, payload: DecisionPacket, ctx: ToolContext) -> DecisionPacket:
        return payload
