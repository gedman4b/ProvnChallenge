"""Fake dataset standing in for the member data service.

Deliberately covers the edge cases the recommendation engine and resilience
layer need to handle: a member with no history (new member), a member whose
history includes a category their partner now excludes, and a member
belonging to a partner_id that the partner config mock doesn't know about
(tests the fail-safe fallback path end to end).
"""

from __future__ import annotations

from datetime import date

from app.models.schemas import Booking, BookingType, LoyaltyTier, MemberProfile

_MEMBERS: dict[str, MemberProfile] = {
    "m-1001": MemberProfile(
        member_id="m-1001",
        partner_id="suntrust-rewards",
        loyalty_tier=LoyaltyTier.GOLD,
        travel_history=[
            Booking(destination="Lisbon, Portugal", booking_type=BookingType.HOTEL,
                     start_date=date(2026, 5, 12), end_date=date(2026, 5, 19)),
            Booking(destination="New York, NY", booking_type=BookingType.FLIGHT,
                     start_date=date(2026, 3, 2), end_date=date(2026, 3, 6)),
            Booking(destination="Austin, TX", booking_type=BookingType.CAR,
                     start_date=date(2025, 12, 20), end_date=date(2025, 12, 27)),
        ],
    ),
    "m-1002": MemberProfile(
        member_id="m-1002",
        partner_id="suntrust-rewards",
        loyalty_tier=LoyaltyTier.SILVER,
        travel_history=[
            Booking(destination="Chicago, IL", booking_type=BookingType.FLIGHT,
                     start_date=date(2026, 6, 1), end_date=date(2026, 6, 4)),
        ],
    ),
    "m-1003": MemberProfile(
        member_id="m-1003",
        partner_id="globalfirst-travel",
        loyalty_tier=LoyaltyTier.PLATINUM,
        travel_history=[
            Booking(destination="Caribbean (multi-port)", booking_type=BookingType.CRUISE,
                     start_date=date(2026, 1, 10), end_date=date(2026, 1, 17)),
            Booking(destination="Barcelona, Spain", booking_type=BookingType.HOTEL,
                     start_date=date(2025, 11, 3), end_date=date(2025, 11, 10)),
            Booking(destination="Rome, Italy", booking_type=BookingType.PACKAGE,
                     start_date=date(2025, 8, 14), end_date=date(2025, 8, 21)),
            Booking(destination="Miami, FL", booking_type=BookingType.FLIGHT,
                     start_date=date(2025, 6, 1), end_date=date(2025, 6, 3)),
        ],
    ),
    "m-1004": MemberProfile(
        member_id="m-1004",
        partner_id="globalfirst-travel",
        loyalty_tier=LoyaltyTier.SILVER,
        travel_history=[
            Booking(destination="Denver, CO", booking_type=BookingType.HOTEL,
                     start_date=date(2026, 2, 5), end_date=date(2026, 2, 9)),
        ],
    ),
    "m-1005": MemberProfile(
        member_id="m-1005",
        partner_id="meridian-points",
        loyalty_tier=LoyaltyTier.GOLD,
        travel_history=[
            Booking(destination="Cancun, Mexico", booking_type=BookingType.PACKAGE,
                     start_date=date(2026, 4, 1), end_date=date(2026, 4, 8)),
            Booking(destination="Seattle, WA", booking_type=BookingType.FLIGHT,
                     start_date=date(2026, 1, 15), end_date=date(2026, 1, 18)),
            Booking(destination="Orlando, FL", booking_type=BookingType.HOTEL,
                     start_date=date(2025, 9, 20), end_date=date(2025, 9, 27)),
            Booking(destination="Nashville, TN", booking_type=BookingType.CAR,
                     start_date=date(2025, 7, 4), end_date=date(2025, 7, 8)),
            Booking(destination="Phoenix, AZ", booking_type=BookingType.FLIGHT,
                     start_date=date(2025, 5, 2), end_date=date(2025, 5, 5)),
        ],
    ),
    "m-1006": MemberProfile(
        member_id="m-1006",
        partner_id="voyage-elite",
        loyalty_tier=LoyaltyTier.PLATINUM,
        travel_history=[
            Booking(destination="Kyoto, Japan", booking_type=BookingType.HOTEL,
                     start_date=date(2026, 4, 20), end_date=date(2026, 4, 30)),
            Booking(destination="Norwegian Fjords", booking_type=BookingType.CRUISE,
                     start_date=date(2026, 2, 1), end_date=date(2026, 2, 12)),
            Booking(destination="Dubai, UAE", booking_type=BookingType.FLIGHT,
                     start_date=date(2025, 12, 1), end_date=date(2025, 12, 8)),
            Booking(destination="Maldives", booking_type=BookingType.PACKAGE,
                     start_date=date(2025, 10, 5), end_date=date(2025, 10, 15)),
            Booking(destination="Zurich, Switzerland", booking_type=BookingType.CAR,
                     start_date=date(2025, 8, 1), end_date=date(2025, 8, 6)),
        ],
    ),
    # partner_id intentionally absent from the partner config mock — exercises
    # the fail-safe fallback path (see PartnerConfigClient).
    "m-1007": MemberProfile(
        member_id="m-1007",
        partner_id="unregistered-partner-x",
        loyalty_tier=LoyaltyTier.GOLD,
        travel_history=[
            Booking(destination="Vancouver, Canada", booking_type=BookingType.FLIGHT,
                     start_date=date(2026, 3, 10), end_date=date(2026, 3, 14)),
        ],
    ),
    # No travel history at all — new member, exercises the "cold start" path
    # of the recommendation engine.
    "m-1008": MemberProfile(
        member_id="m-1008",
        partner_id="suntrust-rewards",
        loyalty_tier=LoyaltyTier.SILVER,
        travel_history=[],
    ),
}


class MemberNotFoundError(Exception):
    def __init__(self, member_id: str):
        self.member_id = member_id
        super().__init__(f"Member {member_id!r} not found")


def lookup_member(member_id: str) -> MemberProfile:
    member = _MEMBERS.get(member_id)
    if member is None:
        raise MemberNotFoundError(member_id)
    return member
