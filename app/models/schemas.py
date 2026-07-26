"""Shared data contracts for the recommendations service.

These models are the boundary between the two mocked upstreams (member data,
partner config), the recommendation engine, and both transports (REST + MCP).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field


class LoyaltyTier(StrEnum):
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class BookingType(StrEnum):
    FLIGHT = "flight"
    HOTEL = "hotel"
    CAR = "car"
    CRUISE = "cruise"
    PACKAGE = "package"


class Booking(BaseModel):
    destination: str
    booking_type: BookingType
    start_date: date
    end_date: date


class MemberProfile(BaseModel):
    member_id: str
    partner_id: str
    loyalty_tier: LoyaltyTier
    # Most recent first, capped at 5 by the (mock) member data service contract.
    travel_history: list[Booking] = Field(default_factory=list)


class PartnerConfig(BaseModel):
    partner_id: str
    display_name: str
    max_recommendations: int | None = Field(
        default=None, description="None means unlimited."
    )
    excluded_categories: list[BookingType] = Field(default_factory=list)
    # True when this config was synthesized by our own fail-safe fallback
    # rather than returned by the partner config service. Surfaced to callers
    # so they never mistake a fallback for an authoritative partner rule.
    is_fallback: bool = False


class Offer(BaseModel):
    offer_id: str
    destination: str
    category: BookingType
    title: str
    description: str
    min_tier: LoyaltyTier | None = None
    tags: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    offer_id: str
    destination: str
    category: BookingType
    title: str
    description: str
    reason: str


class RecommendationResponse(BaseModel):
    member_id: str
    partner_id: str
    recommendations: list[Recommendation]
    applied_rules: dict = Field(default_factory=dict)
    degraded: bool = False
    degraded_reason: str | None = None
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
