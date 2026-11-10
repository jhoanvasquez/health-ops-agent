"""Policy PDF ingestion: parse with page references, chunk, embed, store.

Every chunk keeps its page number so `search_policy` can return citations the
agent can attribute precisely (doc_id + page + excerpt).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.ports import Embedder
from app.db.models import PolicyChunk

CHUNK_CHARS = 1000
CHUNK_OVERLAP = 150


@dataclass
class Chunk:
    """A chunk of policy text with the page it came from."""

    passage: str
    page: int
    doc_id: str


def parse_pages(path: Path | str) -> list[tuple[int, str]]:
    """Return (1-based page number, text) for each page of the PDF."""
    pages: list[tuple[int, str]] = []
    with fitz.open(path) as doc:
        for index, page in enumerate(doc, start=1):
            pages.append((index, page.get_text("text")))
    return pages


def chunk_page(page_no: int, text: str, doc_id: str) -> list[Chunk]:
    """Split one page's text into overlapping, page-tagged chunks."""
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    chunks: list[Chunk] = []
    start = 0
    step = CHUNK_CHARS - CHUNK_OVERLAP
    while start < len(cleaned):
        passage = cleaned[start : start + CHUNK_CHARS]
        chunks.append(Chunk(passage=passage, page=page_no, doc_id=doc_id))
        start += step
    return chunks


def chunk_pdf(path: Path | str, doc_id: str) -> list[Chunk]:
    """Parse and chunk a whole PDF, preserving page references."""
    chunks: list[Chunk] = []
    for page_no, text in parse_pages(path):
        chunks.extend(chunk_page(page_no, text, doc_id))
    return chunks


async def ingest_policy(
    *,
    path: Path | str,
    policy_id: str,
    doc_id: str,
    embedder: Embedder,
    session: AsyncSession,
) -> int:
    """Chunk a policy PDF, embed each chunk, and persist `PolicyChunk` rows.

    Returns the number of chunks stored. The caller owns the transaction (commit).
    """
    chunks = chunk_pdf(path, doc_id)
    for chunk in chunks:
        embedding = await embedder.embed(chunk.passage)
        session.add(
            PolicyChunk(
                policy_id=policy_id,
                doc_id=chunk.doc_id,
                page=chunk.page,
                passage=chunk.passage,
                embedding=embedding,
            )
        )
    return len(chunks)
