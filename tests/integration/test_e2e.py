"""End-to-end acceptance test for the first slice (plan "definition of done").

Submits a synthetic case through the real API and confirms it travels the full
path — API -> queue -> worker -> agent -> persisted decision — reaching a terminal
state. Because it drives the live Anthropic agent, the specific outcome is not
asserted (that is the eval harness's job); this checks the wiring works.

Skipped unless RUN_INTEGRATION=1. Prerequisites (see README):
  - `docker compose up` (api, worker, postgres, rabbitmq, redis, migrations applied)
  - a patient at data/patients/{patient_ref}.json
  - a policy ingested under {policy_id} via app.ingestion.ingest_cli
  - ANTHROPIC_API_KEY and VOYAGE_API_KEY set
"""

from __future__ import annotations

import os
import time
import uuid

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION"),
    reason="integration test: set RUN_INTEGRATION=1 with the stack up (see README)",
)

TERMINAL_STATES = {"decided", "needs_human", "request_info"}


@pytest.mark.integration
def test_case_runs_end_to_end() -> None:
    base = os.getenv("API_BASE_URL", "http://localhost:8000")
    policy_id = os.getenv("E2E_POLICY_ID", "sample-policy")
    patient_ref = os.getenv("E2E_PATIENT_REF", "patient-001")

    created = httpx.post(
        f"{base}/cases",
        json={
            "idempotency_key": str(uuid.uuid4()),
            "policy_id": policy_id,
            "patient_ref": patient_ref,
        },
        timeout=10,
    )
    assert created.status_code == 202
    case_id = created.json()["case_id"]

    state = "received"
    packet = None
    for _ in range(60):
        status = httpx.get(f"{base}/cases/{case_id}", timeout=10)
        assert status.status_code == 200
        body = status.json()
        state = body["state"]
        packet = body.get("packet")
        if state in TERMINAL_STATES:
            break
        time.sleep(2)

    assert state in TERMINAL_STATES, f"case never reached a terminal state (last: {state})"
    if state == "decided":
        assert packet is not None
        assert packet["outcome"] == "approve"
