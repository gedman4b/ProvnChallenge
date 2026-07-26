"""Client for the (read-only) partner configuration service.

This implements the fail-safe policy the whole reliability story leans on:
we can only ever *read* partner rules (hard constraint) and must respect
whatever they say — including when we can't reach them at all. When that
happens we never guess permissive. We serve the last-known-good config
within a bounded staleness window, and beyond that fall back to the
strictest default available (see `fallback_*` settings in app/config.py).
The same fallback applies if the service is reachable but simply has no
record for a given partner_id — an unregistered partner gets the strict
default, not unlimited/uncapped recommendations.
"""

from __future__ import annotations

import abc
import random
import time

from app.config import settings
from app.logging_config import get_logger
from app.mocks.partner_configs import lookup_partner_config
from app.models.schemas import BookingType, PartnerConfig
from app.services.resilience import CircuitBreaker, call_with_resilience

logger = get_logger(__name__)

__all__ = ["PartnerConfigClient", "MockPartnerConfigClient"]


class PartnerConfigClient(abc.ABC):
    @abc.abstractmethod
    async def get_partner_config(self, partner_id: str) -> PartnerConfig: ...


class _CacheEntry:
    __slots__ = ("config", "fetched_at")

    def __init__(self, config: PartnerConfig, fetched_at: float):
        self.config = config
        self.fetched_at = fetched_at


class MockPartnerConfigClient(PartnerConfigClient):
    def __init__(self) -> None:
        self._breaker = CircuitBreaker(
            name="partner_config_service",
            failure_threshold=settings.circuit_breaker_failure_threshold,
            reset_seconds=settings.circuit_breaker_reset_seconds,
        )
        self._cache: dict[str, _CacheEntry] = {}

    @property
    def breaker(self) -> CircuitBreaker:
        return self._breaker

    def _fallback_config(self, partner_id: str) -> PartnerConfig:
        return PartnerConfig(
            partner_id=partner_id,
            display_name=partner_id,
            max_recommendations=settings.fallback_max_recommendations,
            excluded_categories=[
                BookingType(c) for c in settings.fallback_excluded_categories
            ],
            is_fallback=True,
        )

    async def get_partner_config(self, partner_id: str) -> PartnerConfig:
        cached = self._cache.get(partner_id)
        now = time.monotonic()

        if cached is not None and (now - cached.fetched_at) < settings.partner_config_cache_ttl_seconds:
            return cached.config

        try:
            config = await call_with_resilience(
                lambda: self._fetch(partner_id),
                breaker=self._breaker,
                timeout_seconds=settings.downstream_timeout_seconds,
                max_retries=settings.downstream_max_retries,
            )
        except Exception as exc:
            logger.error(
                "partner_config_call_failed",
                extra={"extra_fields": {"partner_id": partner_id, "error": str(exc)}},
            )
            if cached is not None and (now - cached.fetched_at) < settings.partner_config_max_staleness_seconds:
                logger.warning(
                    "partner_config_serving_stale",
                    extra={
                        "extra_fields": {
                            "partner_id": partner_id,
                            "age_seconds": round(now - cached.fetched_at, 1),
                        }
                    },
                )
                return cached.config
            logger.warning(
                "partner_config_fallback_applied",
                extra={"extra_fields": {"partner_id": partner_id, "reason": "service_unavailable"}},
            )
            return self._fallback_config(partner_id)

        if config is None:
            logger.warning(
                "partner_config_fallback_applied",
                extra={"extra_fields": {"partner_id": partner_id, "reason": "unregistered_partner"}},
            )
            return self._fallback_config(partner_id)

        self._cache[partner_id] = _CacheEntry(config=config, fetched_at=now)
        return config

    async def _fetch(self, partner_id: str) -> PartnerConfig | None:
        if random.random() < settings.mock_partner_config_failure_rate:
            raise TimeoutError("simulated partner config service timeout")
        return lookup_partner_config(partner_id)
