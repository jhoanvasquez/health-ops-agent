"""API tests with dependency overrides — no database, broker, or Redis."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_db, get_idempotency, get_publisher
from app.db.models import Case, CaseState
from app.main import app

PACKET = {
    "outcome": "approve",
    "confidence": "high",
    "criteria": [
        {"criterion": "c", "met": True, "evidence": [{"doc_id": "d", "page": 1, "excerpt": "x"}]}
    ],
    "summary": "ok",
}


class FakeSession:
    def __init__(self, *, scalar_result: Any = None, get_result: Any = None) -> None:
        self._scalar = scalar_result
        self._get = get_result
        self.added: list[Any] = []
        self.committed = False

    async def scalar(self, stmt: Any) -> Any:
        return self._scalar

    async def get(self, model: Any, ident: Any) -> Any:
        return self._get

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.committed = True

    async def flush(self) -> None:
        pass


class FakePublisher:
    def __init__(self) -> None:
        self.published: list[str] = []

    async def publish_case(self, case_id: str) -> None:
        self.published.append(case_id)


class FakeGuard:
    def __init__(self, acquired: bool = True) -> None:
        self._acquired = acquired

    async def acquire(self, key: str, ttl_seconds: int) -> bool:
        return self._acquired


@contextmanager
def _overrides(deps: dict[Callable[..., Any], Callable[[], Any]]) -> Iterator[None]:
    app.dependency_overrides.update(deps)
    try:
        yield
    finally:
        app.dependency_overrides.clear()


def _write_deps(
    session: FakeSession, publisher: FakePublisher, guard: FakeGuard
) -> dict[Callable[..., Any], Callable[[], Any]]:
    return {
        get_db: lambda: session,
        get_publisher: lambda: publisher,
        get_idempotency: lambda: guard,
    }


def _case(**kw: Any) -> Case:
    defaults: dict[str, Any] = {
        "id": uuid4(),
        "idempotency_key": "k",
        "policy_id": "p",
        "patient_ref": "pt",
        "state": CaseState.received,
    }
    defaults.update(kw)
    return Case(**defaults)


def test_create_case_accepts_and_publishes() -> None:
    session, publisher = FakeSession(scalar_result=None), FakePublisher()
    with _overrides(_write_deps(session, publisher, FakeGuard(True))):
        response = TestClient(app).post(
            "/cases",
            json={"idempotency_key": "abc", "policy_id": "pol", "patient_ref": "patient-001"},
        )
    assert response.status_code == 202
    assert response.json()["state"] == "received"
    assert len(publisher.published) == 1


def test_create_case_is_idempotent() -> None:
    existing = _case(state=CaseState.decided)
    session, publisher = FakeSession(scalar_result=existing), FakePublisher()
    with _overrides(_write_deps(session, publisher, FakeGuard(True))):
        response = TestClient(app).post(
            "/cases",
            json={"idempotency_key": "abc", "policy_id": "pol", "patient_ref": "patient-001"},
        )
    assert response.status_code == 202
    assert response.json()["case_id"] == str(existing.id)
    assert publisher.published == []  # no duplicate event


def test_create_case_rejects_invalid_body() -> None:
    with _overrides(_write_deps(FakeSession(), FakePublisher(), FakeGuard(True))):
        response = TestClient(app).post("/cases", json={"policy_id": "pol"})
    assert response.status_code == 422


def test_get_case_not_found() -> None:
    with _overrides({get_db: lambda: FakeSession(get_result=None)}):
        response = TestClient(app).get(f"/cases/{uuid4()}")
    assert response.status_code == 404


def test_get_case_returns_packet() -> None:
    case = _case(state=CaseState.decided, packet=PACKET)
    with _overrides({get_db: lambda: FakeSession(get_result=case)}):
        response = TestClient(app).get(f"/cases/{case.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "decided"
    assert body["packet"]["outcome"] == "approve"
