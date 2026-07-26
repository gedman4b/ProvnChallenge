"""Fake dataset standing in for the (read-only) partner configuration service.

Real service would be owned by the partner-management team; we only ever
read from it. Deliberately includes a mix of permissive and restrictive
partners so rule enforcement is visibly exercised by the test suite and the
smoke script.
"""

from __future__ import annotations

from app.models.schemas import BookingType, PartnerConfig

_PARTNER_CONFIGS: dict[str, PartnerConfig] = {
    "suntrust-rewards": PartnerConfig(
        partner_id="suntrust-rewards",
        display_name="SunTrust Rewards",
        max_recommendations=3,
        excluded_categories=[],
    ),
    "globalfirst-travel": PartnerConfig(
        partner_id="globalfirst-travel",
        display_name="GlobalFirst Travel Club",
        max_recommendations=None,  # unlimited
        excluded_categories=[BookingType.CRUISE],
    ),
    "meridian-points": PartnerConfig(
        partner_id="meridian-points",
        display_name="Meridian Credit Union Points",
        max_recommendations=1,
        excluded_categories=[BookingType.CRUISE, BookingType.PACKAGE],
    ),
    "voyage-elite": PartnerConfig(
        partner_id="voyage-elite",
        display_name="Voyage Elite",
        max_recommendations=None,
        excluded_categories=[],
    ),
}


def lookup_partner_config(partner_id: str) -> PartnerConfig | None:
    """Returns None (not an exception) for an unknown partner — mirrors a
    real config service returning a 404 for a partner it has no record of.
    Callers decide what "unknown partner" means; we don't invent a default
    here so the fail-safe policy lives in exactly one place
    (PartnerConfigClient)."""
    return _PARTNER_CONFIGS.get(partner_id)
