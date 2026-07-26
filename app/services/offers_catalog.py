"""Static mock offer inventory.

Stands in for arrivia's real offers/inventory (30,000+ itineraries, 700
airlines, 1M+ hotels, 30,000 rental car locations). A hand-picked catalog is
enough to demonstrate ranking + partner rule enforcement without a real
catalog integration in v1.
"""

from __future__ import annotations

from app.models.schemas import BookingType, LoyaltyTier, Offer

OFFERS: list[Offer] = [
    Offer(offer_id="off-hotel-lisbon", destination="Lisbon, Portugal", category=BookingType.HOTEL,
          title="5 Nights in Lisbon's Alfama District",
          description="Boutique riverside hotel, member rate.", tags=["europe", "city"]),
    Offer(offer_id="off-hotel-kyoto", destination="Kyoto, Japan", category=BookingType.HOTEL,
          title="Ryokan Stay in Kyoto", description="Traditional ryokan with private onsen.",
          min_tier=LoyaltyTier.GOLD, tags=["asia", "relaxation"]),
    Offer(offer_id="off-flight-nyc", destination="New York, NY", category=BookingType.FLIGHT,
          title="Round-trip Flights to New York", description="Nonstop from major hubs, member fare.",
          tags=["city", "domestic"]),
    Offer(offer_id="off-flight-tokyo", destination="Tokyo, Japan", category=BookingType.FLIGHT,
          title="Business Class to Tokyo", description="Upgraded fare bundle for elite members.",
          min_tier=LoyaltyTier.PLATINUM, tags=["asia", "premium"]),
    Offer(offer_id="off-car-austin", destination="Austin, TX", category=BookingType.CAR,
          title="Weekend Car Rental in Austin", description="Compact and SUV options, no blackout dates.",
          tags=["domestic", "road-trip"]),
    Offer(offer_id="off-cruise-caribbean", destination="Caribbean (multi-port)", category=BookingType.CRUISE,
          title="7-Night Caribbean Cruise", description="Multi-port itinerary, balcony upgrade included.",
          tags=["beach", "relaxation"]),
    Offer(offer_id="off-cruise-fjords", destination="Norwegian Fjords", category=BookingType.CRUISE,
          title="10-Night Norwegian Fjords Cruise", description="Scenic cruising, premium beverage package.",
          min_tier=LoyaltyTier.GOLD, tags=["europe", "scenic"]),
    Offer(offer_id="off-package-cancun", destination="Cancun, Mexico", category=BookingType.PACKAGE,
          title="All-Inclusive Cancun Getaway", description="Flight + resort bundle, all-inclusive.",
          tags=["beach", "relaxation"]),
    Offer(offer_id="off-package-rome", destination="Rome, Italy", category=BookingType.PACKAGE,
          title="Rome Highlights Package", description="Flight + hotel + skip-the-line tours.",
          tags=["europe", "culture"]),
    Offer(offer_id="off-hotel-denver", destination="Denver, CO", category=BookingType.HOTEL,
          title="Downtown Denver Weekend", description="Ski-season member rate, walkable downtown.",
          tags=["domestic", "adventure"]),
    Offer(offer_id="off-flight-seattle", destination="Seattle, WA", category=BookingType.FLIGHT,
          title="Seattle Getaway Flights", description="Flexible member fares.", tags=["domestic", "city"]),
    Offer(offer_id="off-package-maldives", destination="Maldives", category=BookingType.PACKAGE,
          title="Overwater Villa Package, Maldives", description="Flight + overwater bungalow bundle.",
          min_tier=LoyaltyTier.PLATINUM, tags=["beach", "premium"]),
    Offer(offer_id="off-hotel-orlando", destination="Orlando, FL", category=BookingType.HOTEL,
          title="Orlando Family Resort Stay", description="Near major theme parks, member rate.",
          tags=["domestic", "family"]),
    Offer(offer_id="off-car-nashville", destination="Nashville, TN", category=BookingType.CAR,
          title="Nashville Weekend Rental", description="Unlimited mileage, free additional driver.",
          tags=["domestic", "road-trip"]),
    Offer(offer_id="off-flight-vancouver", destination="Vancouver, Canada", category=BookingType.FLIGHT,
          title="Vancouver Flight Deal", description="Nonstop, member fare.", tags=["domestic", "city"]),
]


def all_offers() -> list[Offer]:
    return list(OFFERS)
