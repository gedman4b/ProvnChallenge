"""Orchestrates a single request across both downstream clients and the rule
engine. Both the MCP tool layer and the REST layer call this — no business
logic is duplicated between transports, so a rule fix only has to happen
once.
"""

from __future__ import annotations

import uuid

from app.logging_config import bind_context, clear_context, get_logger
from app.models.schemas import MemberProfile, PartnerConfig, RecommendationResponse
from app.services.member_client import (
    MemberDataClient,
    MemberNotFoundError,
    MemberServiceUnavailableError,
)
from app.services.partner_config_client import PartnerConfigClient
from app.services.recommendation_engine import (
    build_generic_recommendations,
    build_recommendations,
)

logger = get_logger(__name__)

__all__ = ["RecommendationOrchestrator", "MemberNotFoundError", "MemberServiceUnavailableError"]


class RecommendationOrchestrator:
    def __init__(
        self, member_client: MemberDataClient, partner_config_client: PartnerConfigClient
    ):
        self._member_client = member_client
        self._partner_config_client = partner_config_client

    async def get_member_profile(
        self, member_id: str, request_id: str | None = None
    ) -> MemberProfile:
        request_id = request_id or str(uuid.uuid4())
        bind_context(request_id=request_id, member_id=member_id)
        try:
            return await self._member_client.get_member(member_id)
        finally:
            clear_context()

    async def get_partner_rules(
        self, partner_id: str, request_id: str | None = None
    ) -> PartnerConfig:
        request_id = request_id or str(uuid.uuid4())
        bind_context(request_id=request_id, partner_id=partner_id)
        try:
            return await self._partner_config_client.get_partner_config(partner_id)
        finally:
            clear_context()

    async def get_recommendations(
        self, member_id: str, request_id: str | None = None
    ) -> RecommendationResponse:
        request_id = request_id or str(uuid.uuid4())
        bind_context(request_id=request_id, member_id=member_id)
        try:
            try:
                member = await self._member_client.get_member(member_id)
            except MemberNotFoundError:
                raise
            except MemberServiceUnavailableError:
                logger.error("member_service_unavailable_degrading")
                return await self._degraded_response(member_id)

            bind_context(request_id=request_id, partner_id=member.partner_id, member_id=member_id)
            partner_config = await self._partner_config_client.get_partner_config(
                member.partner_id
            )
            recs, applied_rules = build_recommendations(member, partner_config)
            degraded = partner_config.is_fallback
            return RecommendationResponse(
                member_id=member.member_id,
                partner_id=member.partner_id,
                recommendations=recs,
                applied_rules=applied_rules,
                degraded=degraded,
                degraded_reason=(
                    "partner_rules_unavailable_using_fail_safe_default" if degraded else None
                ),
            )
        finally:
            clear_context()

    async def _degraded_response(self, member_id: str) -> RecommendationResponse:
        # We have no member record, so no partner_id either — we can't
        # legitimately apply a specific partner's rules. Route through the
        # same fail-safe fallback path partner-config outages use, rather
        # than inventing a second "unknown partner" policy.
        partner_config = await self._partner_config_client.get_partner_config(
            "__unresolved_partner__"
        )
        recs, applied_rules = build_generic_recommendations(partner_config)
        return RecommendationResponse(
            member_id=member_id,
            partner_id="unknown",
            recommendations=recs,
            applied_rules=applied_rules,
            degraded=True,
            degraded_reason="member_service_unavailable",
        )
