"""REST transport — mirrors the MCP tool surface for non-agent callers
(manual testing, other internal services, ALB health/readiness checks).
Delegates to the same app.dependencies.orchestrator the MCP layer uses, so
behavior is identical across transports.
"""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query

from app.dependencies import member_client, orchestrator, partner_config_client
from app.logging_config import get_logger
from app.mocks.member_data import MemberNotFoundError
from app.models.schemas import MemberProfile, PartnerConfig, RecommendationResponse
from app.services.member_client import MemberServiceUnavailableError
from app.services.resilience import CircuitState

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Liveness only — deliberately makes no downstream calls. A "deep"
    health check that pings dependencies would let a slow member-data
    outage cascade into ALB marking every task unhealthy simultaneously.
    Circuit breaker state (see /ready) is the signal for that instead."""
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict:
    breakers = {
        "member_data_service": member_client.breaker.state.value,
        "partner_config_service": partner_config_client.breaker.state.value,
    }
    healthy = all(state != CircuitState.OPEN.value for state in breakers.values())
    if not healthy:
        raise HTTPException(status_code=503, detail={"status": "degraded", "breakers": breakers})
    return {"status": "ready", "breakers": breakers}


@router.get("/v1/members/{member_id}", response_model=MemberProfile)
async def get_member(
    member_id: str, x_request_id: str | None = Header(default=None)
) -> MemberProfile:
    try:
        return await orchestrator.get_member_profile(member_id, request_id=x_request_id)
    except MemberNotFoundError:
        raise HTTPException(status_code=404, detail=f"member {member_id!r} not found") from None
    except MemberServiceUnavailableError:
        raise HTTPException(status_code=503, detail="member data service unavailable") from None


@router.get("/v1/recommendations/{member_id}", response_model=RecommendationResponse)
async def get_recommendations(
    member_id: str,
    session_id: str | None = Query(default=None),
    x_request_id: str | None = Header(default=None),
) -> RecommendationResponse:
    try:
        return await orchestrator.get_recommendations(
            member_id, request_id=session_id or x_request_id
        )
    except MemberNotFoundError:
        raise HTTPException(status_code=404, detail=f"member {member_id!r} not found") from None


@router.get("/v1/partners/{partner_id}/rules", response_model=PartnerConfig)
async def get_partner_rules(
    partner_id: str, x_request_id: str | None = Header(default=None)
) -> PartnerConfig:
    return await orchestrator.get_partner_rules(partner_id, request_id=x_request_id)
