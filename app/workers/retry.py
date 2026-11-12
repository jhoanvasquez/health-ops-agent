"""Pure retry-vs-dead-letter logic — no I/O, so it unit-tests without a broker.

Attempt counting rides on RabbitMQ's `x-death` header (incremented each time a
message is dead-lettered through the retry queue), so there is no custom counter
in the message body.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

MAX_ATTEMPTS = 3  # total processing attempts before dead-lettering
RETRY_TTL_MS = 15_000  # delay a failed message waits before it is requeued

RetryAction = Literal["retry", "dead_letter"]


def retry_decision(attempt: int, max_attempts: int = MAX_ATTEMPTS) -> RetryAction:
    """Decide what to do after a failure on this delivery.

    `attempt` is the current 1-based attempt number. Retry while under the budget;
    once the budget is reached, dead-letter.
    """
    return "retry" if attempt < max_attempts else "dead_letter"


def prior_failures(headers: Mapping[str, Any] | None) -> int:
    """Number of prior failed deliveries from the `x-death` header (0 on first delivery).

    Robust to a missing or malformed header — poison messages must not crash the parser.
    """
    if not headers:
        return 0
    x_death = headers.get("x-death")
    if not isinstance(x_death, (list, tuple)):
        return 0
    counts = [
        int(entry["count"]) for entry in x_death if isinstance(entry, Mapping) and "count" in entry
    ]
    return max(counts, default=0)


def current_attempt(headers: Mapping[str, Any] | None) -> int:
    """The 1-based attempt number for the current delivery."""
    return prior_failures(headers) + 1
