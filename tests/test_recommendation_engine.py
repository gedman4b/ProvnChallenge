"""Unit tests for the rule-based recommendation engine. Constructs
MemberProfile/PartnerConfig directly (no mocked network) so these stay fast
and exercise the rule-enforcement boundary in isolation."""

from __future__ import annotations

from datetime import date

from app.models.schemas import (
    Booking,
    BookingType,
    LoyaltyTier,
    MemberProfile,
    PartnerConfig,
)
from app.services.recommendation_engine import (
    build_generic_recommendations,
    build_recommendations,
)


def _member(**overrides) -> MemberProfile:
    defaults = dict(
        member_id="m-test",
        partner_id="p-test",
        loyalty_tier=LoyaltyTier.GOLD,
        travel_history=[],
    )
    defaults.update(overrides)
    return MemberProfile(**defaults)


def _partner(**overrides) -> PartnerConfig:
    defaults = dict(
        partner_id="p-test",
        display_name="Test Partner",
        max_recommendations=None,
        excluded_categories=[],
    )
    defaults.update(overrides)
    return PartnerConfig(**defaults)


def test_cap_is_enforced():
    member = _member()
    partner = _partner(max_recommendations=2)

    recs, applied_rules = build_recommendations(member, partner)

    assert len(recs) == 2
    assert applied_rules["capped"] is True
    assert applied_rules["max_recommendations"] == 2


def test_unlimited_partner_is_not_capped():
    member = _member()
    partner = _partner(max_recommendations=None)

    recs, applied_rules = build_recommendations(member, partner)

    assert len(recs) > 2
    assert applied_rules["capped"] is False


def test_excluded_category_never_appears():
    member = _member(
        travel_history=[
            Booking(
                destination="Caribbean (multi-port)",
                booking_type=BookingType.CRUISE,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 8),
            )
        ]
    )
    partner = _partner(excluded_categories=[BookingType.CRUISE])

    recs, applied_rules = build_recommendations(member, partner)

    assert all(r.category != BookingType.CRUISE for r in recs)
    assert applied_rules["excluded_offer_count"] > 0


def test_tier_gated_offers_hidden_from_lower_tier_member():
    silver = _member(loyalty_tier=LoyaltyTier.SILVER)
    platinum = _member(loyalty_tier=LoyaltyTier.PLATINUM, member_id="m-plat")
    partner = _partner(max_recommendations=None)

    silver_recs, _ = build_recommendations(silver, partner)
    platinum_recs, _ = build_recommendations(platinum, partner)

    assert "off-flight-tokyo" not in {r.offer_id for r in silver_recs}
    assert "off-flight-tokyo" in {r.offer_id for r in platinum_recs}


def test_already_visited_destination_is_not_recommended_again():
    member = _member(
        travel_history=[
            Booking(
                destination="Lisbon, Portugal",
                booking_type=BookingType.HOTEL,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 5),
            )
        ]
    )
    partner = _partner(max_recommendations=None)

    recs, _ = build_recommendations(member, partner)

    assert "off-hotel-lisbon" not in {r.offer_id for r in recs}


def test_cold_start_member_with_no_history_still_gets_recommendations():
    member = _member(travel_history=[])
    partner = _partner(max_recommendations=3)

    recs, applied_rules = build_recommendations(member, partner)

    assert len(recs) == 3
    assert applied_rules["capped"] is True


def test_recommendations_are_deterministic():
    member = _member(
        travel_history=[
            Booking(
                destination="Austin, TX",
                booking_type=BookingType.CAR,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 5),
            )
        ]
    )
    partner = _partner(max_recommendations=5)

    first, _ = build_recommendations(member, partner)
    second, _ = build_recommendations(member, partner)

    assert [r.offer_id for r in first] == [r.offer_id for r in second]


def test_generic_recommendations_exclude_tier_gated_offers():
    partner = _partner(max_recommendations=None)

    recs, _ = build_generic_recommendations(partner)

    # No known loyalty tier when degraded, so nothing tier-restricted should
    # ever be shown.
    assert "off-flight-tokyo" not in {r.offer_id for r in recs}
    assert "off-package-maldives" not in {r.offer_id for r in recs}


def test_generic_recommendations_respect_partner_exclusions():
    partner = _partner(excluded_categories=[BookingType.CRUISE, BookingType.PACKAGE])

    recs, _ = build_generic_recommendations(partner)

    assert all(r.category not in (BookingType.CRUISE, BookingType.PACKAGE) for r in recs)
