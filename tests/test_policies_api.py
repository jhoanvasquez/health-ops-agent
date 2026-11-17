"""Policy ingestion endpoint — no database or embedding API (overrides)."""

from __future__ import annotations

from typing import Any

import fitz  # PyMuPDF
from fastapi.testclient import TestClient

from app.api.deps import get_db, get_embedder
from app.main import app


class StubEmbedder:
    async def embed(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


class RecordingSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.committed = False

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.committed = True


def _pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data: bytes = doc.tobytes()
    doc.close()
    return data


def _client(session: RecordingSession) -> TestClient:
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_embedder] = StubEmbedder
    return TestClient(app)


def test_ingest_stores_chunks_and_commits() -> None:
    session = RecordingSession()
    pdf = _pdf_bytes("Prior imaging is required.")
    try:
        response = _client(session).post(
            "/policies",
            data={"policy_id": "sample-policy", "doc_id": "policy-doc-1"},
            files={"file": ("policy.pdf", pdf, "application/pdf")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["policy_id"] == "sample-policy"
    assert body["doc_id"] == "policy-doc-1"
    assert body["chunks"] == len(session.added)
    assert body["chunks"] >= 1
    assert session.committed
    assert all(chunk.policy_id == "sample-policy" for chunk in session.added)


def test_ingest_rejects_non_pdf() -> None:
    session = RecordingSession()
    try:
        response = _client(session).post(
            "/policies",
            data={"policy_id": "p", "doc_id": "d"},
            files={"file": ("note.txt", b"hello", "text/plain")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 415
    assert session.added == []


def test_ingest_rejects_empty_file() -> None:
    session = RecordingSession()
    try:
        response = _client(session).post(
            "/policies",
            data={"policy_id": "p", "doc_id": "d"},
            files={"file": ("empty.pdf", b"", "application/pdf")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
