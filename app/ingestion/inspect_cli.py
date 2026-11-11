"""Probe retrieval: embed a query and show what `search_policy` returns, with scores.

See the embedding at work — the query vector and the nearest policy passages by
cosine similarity. Run inside the worker container (it has the Voyage key + DB):

    python -m app.ingestion.inspect_cli <policy_id> "<query>" [top_k]

Example:
    python -m app.ingestion.inspect_cli sample-policy "failed physical therapy" 5
"""

from __future__ import annotations

import asyncio
import sys

from app.agent.tools.stores import PgPolicyStore
from app.db.base import SessionFactory
from app.ingestion.embeddings import VoyageEmbedder


async def _run(policy_id: str, query: str, top_k: int) -> None:
    embedder = VoyageEmbedder(input_type="query")
    vector = await embedder.embed(query)
    preview = [round(value, 4) for value in vector[:5]]
    print(f"query:     {query!r}")
    print(f"embedding: dim={len(vector)}  first5={preview}")

    async with SessionFactory() as session:
        passages = await PgPolicyStore(session).search(
            policy_id=policy_id, embedding=vector, top_k=top_k
        )

    if not passages:
        print(f"\nno matches for policy {policy_id!r} (is it ingested?)")
        return

    print(f"\ntop {len(passages)} passages for policy {policy_id!r} (higher score = closer):")
    for rank, passage in enumerate(passages, start=1):
        print(f"\n[{rank}] score={passage.score:.4f}  doc={passage.doc_id}  page={passage.page}")
        print(f"    {passage.passage[:220]}")


def main() -> None:
    if len(sys.argv) < 3:
        print('usage: python -m app.ingestion.inspect_cli <policy_id> "<query>" [top_k]')
        raise SystemExit(2)
    policy_id = sys.argv[1]
    query = sys.argv[2]
    top_k = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    asyncio.run(_run(policy_id, query, top_k))


if __name__ == "__main__":
    main()
