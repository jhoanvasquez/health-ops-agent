"""API tests with dependency overrides — no database, broker, or Redis."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
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


class _Scalars:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def all(self) -> list[Any]:
        return self._items


class FakeSession:
    def __init__(
        self,
        *,
        scalar_result: Any = None,
        get_result: Any = None,
        scalars_result: list[Any] | None = None,
    ) -> None:
        self._scalar = scalar_result
        self._get = get_result
        self._scalars = scalars_result or []
        self.added: list[Any] = []
        self.committed = False

    async def scalar(self, stmt: Any) -> Any:
        return self._scalar

    async def scalars(self, stmt: Any) -> _Scalars:
        return _Scalars(self._scalars)

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
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
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


def test_list_pending_review_returns_summaries() -> None:
    pending = _case(state=CaseState.needs_human, packet={**PACKET, "outcome": "deny"})
    with _overrides({get_db: lambda: FakeSession(scalars_result=[pending])}):
        response = TestClient(app).get("/cases?pending_review=true")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["case_id"] == str(pending.id)
    assert body[0]["recommended_outcome"] == "deny"
    assert body[0]["state"] == "needs_human"


def test_review_records_decision() -> None:
    case = _case(state=CaseState.needs_human, packet={**PACKET, "outcome": "deny"})
    session = FakeSession(get_result=case)
    with _overrides({get_db: lambda: session}):
        response = TestClient(app).post(
            f"/cases/{case.id}/review", json={"decision": "deny", "note": "agree"}
        )
    assert response.status_code == 200
    assert response.json()["review_decision"] == "deny"
    assert case.review_decision == "deny"
    assert case.review_note == "agree"
    assert case.reviewed_at is not None
    assert session.committed
    assert any(getattr(obj, "tool", None) == "human_review" for obj in session.added)


def test_review_already_reviewed_conflicts() -> None:
    case = _case(state=CaseState.needs_human, review_decision="approve")
    with _overrides({get_db: lambda: FakeSession(get_result=case)}):
        response = TestClient(app).post(f"/cases/{case.id}/review", json={"decision": "deny"})
    assert response.status_code == 409


def test_review_unknown_case_404() -> None:
    with _overrides({get_db: lambda: FakeSession(get_result=None)}):
        response = TestClient(app).post(f"/cases/{uuid4()}/review", json={"decision": "deny"})
    assert response.status_code == 404


def test_review_rejects_invalid_decision() -> None:
    case = _case(state=CaseState.needs_human)
    with _overrides({get_db: lambda: FakeSession(get_result=case)}):
        response = TestClient(app).post(f"/cases/{case.id}/review", json={"decision": "maybe"})
    assert response.status_code == 422


def test_detail_includes_review() -> None:
    case = _case(
        state=CaseState.needs_human,
        packet={**PACKET, "outcome": "deny"},
        review_decision="deny",
        review_note="confirmed",
        reviewed_at=datetime(2026, 2, 1, tzinfo=UTC),
    )
    with _overrides({get_db: lambda: FakeSession(get_result=case)}):
        response = TestClient(app).get(f"/cases/{case.id}")
    body = response.json()
    assert body["review_decision"] == "deny"
    assert body["review_note"] == "confirmed"
    assert body["reviewed_at"] is not None
