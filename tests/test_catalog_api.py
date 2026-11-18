"""Catalog endpoints (/policies, /patients) — no database (overrides)."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.agent.tools.patient_repo import FilePatientRepository
from app.api.deps import get_db
from app.api.patients import get_patients
from app.main import app


class _Result:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return self._rows


class FakeSession:
    """Minimal stand-in: `execute(...).all()` returns preset rows."""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    async def execute(self, stmt: Any) -> _Result:
        return _Result(self._rows)


class FakeRepo:
    def __init__(self, refs: list[tuple[str, str]]) -> None:
        self._refs = refs

    async def list_refs(self) -> list[tuple[str, str]]:
        return self._refs


def test_list_policies_returns_summaries() -> None:
    session = FakeSession([("sample-policy", 2), ("knee-mri", 5)])
    app.dependency_overrides[get_db] = lambda: session
    try:
        response = TestClient(app).get("/policies")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == [
        {"policy_id": "sample-policy", "chunks": 2},
        {"policy_id": "knee-mri", "chunks": 5},
    ]


def test_list_policies_empty() -> None:
    app.dependency_overrides[get_db] = lambda: FakeSession([])
    try:
        response = TestClient(app).get("/policies")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []


def test_list_patients_returns_summaries() -> None:
    repo = FakeRepo([("patient-001", "Test Synthetic"), ("patient-002", "Sample Synthetic")])
    app.dependency_overrides[get_patients] = lambda: repo
    try:
        response = TestClient(app).get("/patients")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == [
        {"patient_ref": "patient-001", "display_name": "Test Synthetic"},
        {"patient_ref": "patient-002", "display_name": "Sample Synthetic"},
    ]


async def test_list_refs_reads_real_fixtures() -> None:
    refs = await FilePatientRepository().list_refs()
    by_ref = dict(refs)
    assert "patient-001" in by_ref
    assert by_ref["patient-001"] == "Test Synthetic"  # given+family from the bundle


async def test_list_refs_missing_dir_is_empty() -> None:
    assert await FilePatientRepository(root="data/does-not-exist").list_refs() == []
