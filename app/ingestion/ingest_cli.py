"""Ingest a policy PDF into pgvector.

Usage:
    python -m app.ingestion.ingest_cli <pdf_path> <policy_id> <doc_id>

Requires a reachable database (DATABASE_URL) and VOYAGE_API_KEY. Synthetic /
non-PHI policy documents only.
"""

from __future__ import annotations

import asyncio
import sys

from app.db.base import SessionFactory
from app.ingestion.embeddings import VoyageEmbedder
from app.ingestion.policy_pdf import ingest_policy


async def _run(pdf_path: str, policy_id: str, doc_id: str) -> int:
    embedder = VoyageEmbedder(input_type="document")
    async with SessionFactory() as session:
        count = await ingest_policy(
            path=pdf_path,
            policy_id=policy_id,
            doc_id=doc_id,
            embedder=embedder,
            session=session,
        )
        await session.commit()
    return count


def main() -> None:
    if len(sys.argv) != 4:
        print("usage: python -m app.ingestion.ingest_cli <pdf_path> <policy_id> <doc_id>")
        raise SystemExit(2)
    _, pdf_path, policy_id, doc_id = sys.argv
    count = asyncio.run(_run(pdf_path, policy_id, doc_id))
    print(f"ingested {count} chunks for policy '{policy_id}' (doc '{doc_id}')")


if __name__ == "__main__":
    main()
