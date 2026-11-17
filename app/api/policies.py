"""Policy ingestion endpoint.

How a policy enters the system in a deployed environment where there is no shell
access to the worker: upload the PDF over HTTP, and it is chunked by page,
embedded, and stored in pgvector. Synthetic / non-PHI policy documents only.
"""

from __future__ import annotations

import os
import tempfile
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.ports import Embedder
from app.api.deps import get_db, get_embedder
from app.api.schemas import PolicyIngestedResponse
from app.ingestion.policy_pdf import ingest_policy

router = APIRouter(prefix="/policies", tags=["policies"])

# Browsers send application/pdf; some clients (curl without -H) send octet-stream.
_PDF_CONTENT_TYPES = frozenset({"application/pdf", "application/octet-stream"})


@router.post("", response_model=PolicyIngestedResponse, status_code=status.HTTP_201_CREATED)
async def ingest_policy_pdf(
    policy_id: Annotated[str, Form(min_length=1, max_length=255)],
    doc_id: Annotated[str, Form(min_length=1, max_length=255)],
    file: Annotated[UploadFile, File()],
    session: Annotated[AsyncSession, Depends(get_db)],
    embedder: Annotated[Embedder, Depends(get_embedder)],
) -> PolicyIngestedResponse:
    """Ingest a synthetic policy PDF: chunk by page, embed, store.

    Multipart form fields: `policy_id`, `doc_id`, and `file` (the PDF). Returns the
    number of chunks stored. Rejects non-PDF uploads (415) and empty files (400).
    """
    if file.content_type not in _PDF_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="expected a PDF upload",
        )
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty file")

    # PyMuPDF opens from a path; write to a short-lived temp file, then remove it.
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        count = await ingest_policy(
            path=tmp_path,
            policy_id=policy_id,
            doc_id=doc_id,
            embedder=embedder,
            session=session,
        )
        await session.commit()
    finally:
        os.unlink(tmp_path)

    return PolicyIngestedResponse(policy_id=policy_id, doc_id=doc_id, chunks=count)
