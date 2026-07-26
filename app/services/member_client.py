"""Client for the member data service.

Defines the interface the rest of the app depends on, plus a Mock
implementation backed by app/mocks/member_data.py. Swapping in the real
HTTP-backed member data service later means adding one new class
(e.g. `HttpMemberDataClient`) that satisfies this interface — nothing else in
the codebase changes.
"""

from __future__ import annotations

import abc
import random

from app.config import settings
from app.logging_config import get_logger
from app.mocks.member_data import MemberNotFoundError, lookup_member
from app.models.schemas import MemberProfile
from app.services.resilience import CircuitBreaker, call_with_resilience

logger = get_logger(__name__)

__all__ = [
    "MemberDataClient",
    "MockMemberDataClient",
    "MemberNotFoundError",
    "MemberServiceUnavailableError",
]


class MemberServiceUnavailableError(Exception):
    """The member data service couldn't be reached after retries, or its
    circuit breaker is open. Distinct from MemberNotFoundError (a valid
    "no such member" response from a healthy service)."""


class MemberDataClient(abc.ABC):
    @abc.abstractmethod
    async def get_member(self, member_id: str) -> MemberProfile: ...


class MockMemberDataClient(MemberDataClient):
    """Simulates the real member data service: in-memory lookup with
    injectable failure for local resilience testing
    (ARRIVIA_MOCK_MEMBER_SERVICE_FAILURE_RATE)."""

    def __init__(self) -> None:
        self._breaker = CircuitBreaker(
            name="member_data_service",
            failure_threshold=settings.circuit_breaker_failure_threshold,
            reset_seconds=settings.circuit_breaker_reset_seconds,
        )

    @property
    def breaker(self) -> CircuitBreaker:
        return self._breaker

    async def get_member(self, member_id: str) -> MemberProfile:
        try:
            return await call_with_resilience(
                lambda: self._fetch(member_id),
                breaker=self._breaker,
                timeout_seconds=settings.downstream_timeout_seconds,
                max_retries=settings.downstream_max_retries,
                non_retryable=(MemberNotFoundError,),
            )
        except MemberNotFoundError:
            raise
        except Exception as exc:
            logger.error(
                "member_service_call_failed", extra={"extra_fields": {"error": str(exc)}}
            )
            raise MemberServiceUnavailableError(str(exc)) from exc

    async def _fetch(self, member_id: str) -> MemberProfile:
        if random.random() < settings.mock_member_service_failure_rate:
            raise TimeoutError("simulated member data service timeout")
        return lookup_member(member_id)
