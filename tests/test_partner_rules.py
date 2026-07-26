"""Tests for the partner config client's fail-safe policy: unknown/unreachable
partner rules must resolve to the strictest default, never to something
permissive. This is the property the whole multi-tenant safety story rests
on."""

from __future__ import annotations

import asyncio

from app.config import settings
from app.services.partner_config_client import MockPartnerConfigClient


def test_unregistered_partner_gets_strict_fallback_not_unlimited():
    client = MockPartnerConfigClient()

    config = asyncio.run(client.get_partner_config("no-such-partner"))

    assert config.is_fallback is True
    assert config.max_recommendations == settings.fallback_max_recommendations
    assert set(c.value for c in config.excluded_categories) == set(
        settings.fallback_excluded_categories
    )


def test_known_partner_is_cached_across_calls(monkeypatch):
    calls = {"count": 0}
    from app.mocks.partner_configs import lookup_partner_config as real_lookup

    def counting_lookup(partner_id: str):
        calls["count"] += 1
        return real_lookup(partner_id)

    monkeypatch.setattr(
        "app.services.partner_config_client.lookup_partner_config", counting_lookup
    )
    monkeypatch.setattr(settings, "partner_config_cache_ttl_seconds", 300.0)

    client = MockPartnerConfigClient()
    asyncio.run(client.get_partner_config("suntrust-rewards"))
    asyncio.run(client.get_partner_config("suntrust-rewards"))

    assert calls["count"] == 1


def test_stale_config_served_within_staleness_window_then_falls_back(monkeypatch):
    monkeypatch.setattr(settings, "partner_config_cache_ttl_seconds", 0.0)
    monkeypatch.setattr(settings, "downstream_max_retries", 0)

    client = MockPartnerConfigClient()

    good = asyncio.run(client.get_partner_config("suntrust-rewards"))
    assert good.is_fallback is False

    monkeypatch.setattr(settings, "mock_partner_config_failure_rate", 1.0)
    monkeypatch.setattr(settings, "partner_config_max_staleness_seconds", 100.0)

    served = asyncio.run(client.get_partner_config("suntrust-rewards"))
    assert served.is_fallback is False  # stale-but-known, not the strict fallback
    assert served.partner_id == "suntrust-rewards"

    monkeypatch.setattr(settings, "partner_config_max_staleness_seconds", -1.0)
    fallback = asyncio.run(client.get_partner_config("suntrust-rewards"))
    assert fallback.is_fallback is True
