"""Tests for the pure retry/dead-letter logic."""

from __future__ import annotations

from app.workers.retry import MAX_ATTEMPTS, current_attempt, prior_failures, retry_decision


def test_retry_decision_boundaries() -> None:
    assert retry_decision(1, 3) == "retry"
    assert retry_decision(2, 3) == "retry"
    assert retry_decision(3, 3) == "dead_letter"
    assert retry_decision(4, 3) == "dead_letter"


def test_prior_failures_absent_header() -> None:
    assert prior_failures(None) == 0
    assert prior_failures({}) == 0
    assert prior_failures({"x-death": []}) == 0


def test_prior_failures_reads_count() -> None:
    headers = {"x-death": [{"queue": "cases.process", "reason": "rejected", "count": 2}]}
    assert prior_failures(headers) == 2


def test_prior_failures_takes_max_across_entries() -> None:
    assert prior_failures({"x-death": [{"count": 2}, {"count": 3}]}) == 3


def test_prior_failures_malformed_is_zero() -> None:
    assert prior_failures({"x-death": "not-a-list"}) == 0
    assert prior_failures({"x-death": [{"no_count": 1}]}) == 0


def test_current_attempt() -> None:
    assert current_attempt(None) == 1
    assert current_attempt({"x-death": [{"count": 2}]}) == 3


def test_full_sequence_three_attempts_then_dead_letter() -> None:
    # attempt 1 and 2 retry; the 3rd failure dead-letters
    assert retry_decision(current_attempt(None), MAX_ATTEMPTS) == "retry"
    assert retry_decision(current_attempt({"x-death": [{"count": 1}]}), MAX_ATTEMPTS) == "retry"
    assert (
        retry_decision(current_attempt({"x-death": [{"count": 2}]}), MAX_ATTEMPTS) == "dead_letter"
    )
