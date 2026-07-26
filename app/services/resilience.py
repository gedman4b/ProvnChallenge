"""Timeout + bounded retry + a small in-process circuit breaker.

Hand-rolled rather than a third-party dependency: the behavior needed here is
small, easy to unit test deterministically, and one less unfamiliar failure
mode to reason about at 2am. One CircuitBreaker instance per downstream
client instance (member data, partner config) — a flaky partner config
lookup should never affect member data calls or vice versa.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TypeVar

from app.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised instead of calling a dependency we've already given up on."""


class CircuitBreaker:
    def __init__(self, *, name: str, failure_threshold: int, reset_seconds: float):
        self.name = name
        self._failure_threshold = failure_threshold
        self._reset_seconds = reset_seconds
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> CircuitState:
        if self._state is CircuitState.OPEN and self._opened_at is not None:
            if time.monotonic() - self._opened_at >= self._reset_seconds:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def on_success(self) -> None:
        if self._state is not CircuitState.CLOSED:
            logger.info(
                "circuit_breaker_closed", extra={"extra_fields": {"dependency": self.name}}
            )
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._opened_at = None

    def on_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._failure_threshold:
            if self._state is not CircuitState.OPEN:
                logger.warning(
                    "circuit_breaker_opened",
                    extra={
                        "extra_fields": {
                            "dependency": self.name,
                            "consecutive_failures": self._consecutive_failures,
                        }
                    },
                )
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()

    def before_call(self) -> None:
        if self.state is CircuitState.OPEN:
            raise CircuitOpenError(f"circuit open for dependency={self.name!r}")


async def call_with_resilience(
    fn: Callable[[], Awaitable[T]],
    *,
    breaker: CircuitBreaker,
    timeout_seconds: float,
    max_retries: int,
    non_retryable: tuple[type[Exception], ...] = (),
) -> T:
    """Runs fn() under a timeout, retrying transient failures with backoff.
    Short-circuits immediately (no call attempted) if the breaker is open.

    `non_retryable` exceptions (e.g. "member not found") pass straight
    through untouched: they're a valid business response from a healthy
    dependency, not a signal that the dependency is failing, so they must
    never consume a retry or count toward opening the breaker.
    """
    breaker.before_call()

    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            result = await asyncio.wait_for(fn(), timeout=timeout_seconds)
        except non_retryable:
            raise
        except Exception as exc:  # deliberately broad: this *is* the resilience boundary
            last_exc = exc
            if attempt < max_retries:
                await asyncio.sleep(0.05 * (2**attempt))
                continue
            breaker.on_failure()
            raise
        else:
            breaker.on_success()
            return result

    assert last_exc is not None  # pragma: no cover - unreachable, satisfies type checkers
    raise last_exc
