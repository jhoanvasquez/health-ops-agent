"""`get_patient` tool — fetch synthetic clinical data for one patient."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.agent.tools.base import Tool, ToolContext, ToolError


class GetPatientInput(BaseModel):
    patient_ref: str = Field(
        description="The case's patient reference, e.g. 'patient-001'.",
    )


class GetPatientTool(Tool[GetPatientInput]):
    name = "get_patient"
    description = (
        "Fetch the relevant clinical data for one synthetic patient from the record. "
        "Use when you need patient facts (conditions, medications, procedures, "
        "observations) to evaluate a criterion. Do NOT use to search payer policy "
        "wording (use search_policy) or to judge whether a criterion is met (use "
        "check_criterion). "
        "Input: patient_ref (string, the case's patient reference, e.g. 'patient-001'). "
        "Returns the patient's FHIR resources as a JSON object; an unknown reference "
        "returns a non-retryable error object. Read-only."
    )
    input_model = GetPatientInput

    async def run(self, payload: GetPatientInput, ctx: ToolContext) -> Any:
        resource = await ctx.patients.get(payload.patient_ref)
        if resource is None:
            return ToolError(
                error=f"patient {payload.patient_ref!r} not found",
                retryable=False,
            )
        return resource
