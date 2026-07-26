"""Rule-based recommendation ranking + partner rule enforcement.

Deliberately not ML in v1 (see README "Later" section for why): this needs
to be explainable, deterministic, fast to unit test, and safe to reason
about at 2am when a partner asks "why did your service show a cruise offer
to a member on a partner that excludes cruises." A ranking model can layer
on top of this later without touching the rule-enforcement boundary, which
is the part that actually has to be correct.
"""

from __future__ import annotations

from collections import Counter

from app.models.schemas import (
    BookingType,
    LoyaltyTier,
    MemberProfile,
    Offer,
    PartnerConfig,
    Recommendation,
)
from app.services.offers_catalog import all_offers

_TIER_RANK = {LoyaltyTier.SILVER: 0, LoyaltyTier.GOLD: 1, LoyaltyTier.PLATINUM: 2}


def _meets_tier(offer: Offer, member_tier: LoyaltyTier) -> bool:
    if offer.min_tier is None:
        return True
    return _TIER_RANK[member_tier] >= _TIER_RANK[offer.min_tier]


def _category_affinity(member: MemberProfile) -> Counter:
    """Recency-weighted booking-type affinity. travel_history is
    most-recent-first (member data service contract), so earlier entries get
    more weight — a cruise booked last month should influence rankings more
    than one from a year ago."""
    affinity: Counter = Counter()
    for index, booking in enumerate(member.travel_history):
        affinity[booking.booking_type] += max(1, 5 - index)
    return affinity


def _rationale(offer: Offer, affinity: Counter) -> str:
    if affinity[offer.category] > 0:
        return f"Matches your recent {offer.category.value} bookings."
    return f"Popular {offer.category.value} pick for members at your tier."


def build_recommendations(
    member: MemberProfile, partner_config: PartnerConfig
) -> tuple[list[Recommendation], dict]:
    """Returns (recommendations, applied_rules). applied_rules documents
    exactly what was filtered/capped and why, so a caller (or the
    `list_partner_recommendation_rules` MCP tool) can explain the result to
    an end user or to on-call without re-deriving it."""
    visited_destinations = {b.destination.lower() for b in member.travel_history}
    affinity = _category_affinity(member)
    excluded: set[BookingType] = set(partner_config.excluded_categories)

    excluded_count = 0
    candidates: list[Offer] = []
    for offer in all_offers():
        if offer.category in excluded:
            excluded_count += 1
            continue
        if not _meets_tier(offer, member.loyalty_tier):
            continue
        if offer.destination.lower() in visited_destinations:
            continue
        candidates.append(offer)

    # Deterministic: sort by affinity desc, then offer_id for a stable
    # tie-break. No randomness anywhere in this path — required for the
    # response to be reproducible when debugging a partner complaint.
    candidates.sort(key=lambda o: (-affinity[o.category], o.offer_id))

    cap = partner_config.max_recommendations
    capped = cap is not None and len(candidates) > cap
    if cap is not None:
        candidates = candidates[:cap]

    recommendations = [
        Recommendation(
            offer_id=offer.offer_id,
            destination=offer.destination,
            category=offer.category,
            title=offer.title,
            description=offer.description,
            reason=_rationale(offer, affinity),
        )
        for offer in candidates
    ]

    applied_rules = {
        "partner_id": partner_config.partner_id,
        "max_recommendations": partner_config.max_recommendations,
        "excluded_categories": [c.value for c in partner_config.excluded_categories],
        "excluded_offer_count": excluded_count,
        "capped": capped,
        "used_fallback_partner_config": partner_config.is_fallback,
    }
    return recommendations, applied_rules


def build_generic_recommendations(partner_config: PartnerConfig) -> tuple[list[Recommendation], dict]:
    """Used when the member service is unreachable — no personalization
    signal available, so we return partner-rule-compliant popular picks
    instead of failing the request outright. Caller must set `degraded` on
    the response; this function only concerns itself with rule enforcement,
    same as build_recommendations."""
    excluded: set[BookingType] = set(partner_config.excluded_categories)
    excluded_count = 0
    candidates: list[Offer] = []
    for offer in all_offers():
        if offer.category in excluded:
            excluded_count += 1
            continue
        if offer.min_tier is not None:
            continue  # no tier known — only show broadly-eligible offers
        candidates.append(offer)

    candidates.sort(key=lambda o: o.offer_id)

    cap = partner_config.max_recommendations
    capped = cap is not None and len(candidates) > cap
    if cap is not None:
        candidates = candidates[:cap]

    recommendations = [
        Recommendation(
            offer_id=offer.offer_id,
            destination=offer.destination,
            category=offer.category,
            title=offer.title,
            description=offer.description,
            reason="Popular pick — personalization unavailable right now.",
        )
        for offer in candidates
    ]
    applied_rules = {
        "partner_id": partner_config.partner_id,
        "max_recommendations": partner_config.max_recommendations,
        "excluded_categories": [c.value for c in partner_config.excluded_categories],
        "excluded_offer_count": excluded_count,
        "capped": capped,
        "used_fallback_partner_config": partner_config.is_fallback,
    }
    return recommendations, applied_rules
