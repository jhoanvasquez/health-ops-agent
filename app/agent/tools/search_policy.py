"""`search_policy` tool — semantic search over ingested payer policy chunks."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.agent.tools.base import Tool, ToolContext
from app.agent.tools.ports import PolicyPassage


class SearchPolicyInput(BaseModel):
    query: str = Field(description="Plain-language criterion to search for.")
    policy_id: str = Field(description="Identifier of the policy to search within.")
    top_k: int = Field(default=5, ge=1, le=10, description="How many passages to return (1-10).")


class SearchPolicyTool(Tool[SearchPolicyInput]):
    name = "search_policy"
    description = (
        "Search the payer policy documents for passages relevant to a clinical "
        "criterion. Use when you need the exact policy wording for a procedure or "
        "criterion. Do NOT use to look up patient data (use get_patient) or to judge "
        "whether a criterion is met (use check_criterion). "
        "Input: query (plain-language criterion), policy_id (string), top_k (integer "
        "1-10, default 5). "
        "Returns a list of {passage, page, doc_id, score}; an empty list means no "
        "match. Read-only. On retrieval failure returns an error object with a "
        "retryable flag."
    )
    input_model = SearchPolicyInput

    async def run(self, payload: SearchPolicyInput, ctx: ToolContext) -> list[PolicyPassage]:
        embedding = await ctx.embedder.embed(payload.query)
        return await ctx.policy_store.search(
            policy_id=payload.policy_id,
            embedding=embedding,
            top_k=payload.top_k,
        )
