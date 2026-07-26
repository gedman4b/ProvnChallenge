"""Unit tests for the shared timeout/retry/circuit-breaker helper. These are
what give us confidence the on-call failure-mode story in the README is
actually true, not just described."""

from __future__ import annotations

import asyncio
import time

import pytest

from app.services.resilience import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    call_with_resilience,
)


def test_breaker_opens_after_threshold_consecutive_failures():
    breaker = CircuitBreaker(name="test", failure_threshold=3, reset_seconds=60)

    async def always_fails():
        raise RuntimeError("boom")

    for _ in range(3):
        with pytest.raises(RuntimeError):
            asyncio.run(
                call_with_resilience(always_fails, breaker=breaker, timeout_seconds=1, max_retries=0)
            )

    assert breaker.state == CircuitState.OPEN


def test_open_breaker_short_circuits_without_calling_dependency():
    breaker = CircuitBreaker(name="test", failure_threshold=1, reset_seconds=60)
    calls = {"count": 0}

    async def fails():
        calls["count"] += 1
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        asyncio.run(call_with_resilience(fails, breaker=breaker, timeout_seconds=1, max_retries=0))
    assert breaker.state == CircuitState.OPEN

    with pytest.raises(CircuitOpenError):
        asyncio.run(call_with_resilience(fails, breaker=breaker, timeout_seconds=1, max_retries=0))

    assert calls["count"] == 1  # the second call never reached the dependency


def test_breaker_half_opens_after_reset_window():
    breaker = CircuitBreaker(name="test", failure_threshold=1, reset_seconds=0.05)

    async def fails():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        asyncio.run(call_with_resilience(fails, breaker=breaker, timeout_seconds=1, max_retries=0))
    assert breaker.state == CircuitState.OPEN

    time.sleep(0.1)
    assert breaker.state == CircuitState.HALF_OPEN


def test_retry_then_success_closes_breaker():
    breaker = CircuitBreaker(name="test", failure_threshold=5, reset_seconds=60)
    attempts = {"count": 0}

    async def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("transient")
        return "ok"

    result = asyncio.run(
        call_with_resilience(flaky, breaker=breaker, timeout_seconds=1, max_retries=5)
    )

    assert result == "ok"
    assert breaker.state == CircuitState.CLOSED


def test_non_retryable_exception_bypasses_retry_and_breaker():
    """A "member not found" style business response must never be retried
    or trip the breaker — it's a valid answer from a healthy dependency."""
    breaker = CircuitBreaker(name="test", failure_threshold=1, reset_seconds=60)

    class NotFound(Exception):
        pass

    attempts = {"count": 0}

    async def not_found():
        attempts["count"] += 1
        raise NotFound()

    with pytest.raises(NotFound):
        asyncio.run(
            call_with_resilience(
                not_found,
                breaker=breaker,
                timeout_seconds=1,
                max_retries=3,
                non_retryable=(NotFound,),
            )
        )

    assert attempts["count"] == 1
    assert breaker.state == CircuitState.CLOSED


def test_timeout_counts_as_a_failure():
    breaker = CircuitBreaker(name="test", failure_threshold=1, reset_seconds=60)

    async def hangs():
        await asyncio.sleep(1)

    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(call_with_resilience(hangs, breaker=breaker, timeout_seconds=0.05, max_retries=0))

    assert breaker.state == CircuitState.OPEN
