"""MCP tool definitions for the Agentic Travel Recommendations API.

Exposes a small, deliberately read-only tool surface (see README "MCP tool
surface") that any MCP-compatible agent can discover via `tools/list` and
invoke via `tools/call`. Every tool is a thin wrapper over
`app.dependencies.orchestrator` — no business logic lives here, so the REST
transport in app/api/routes.py behaves identically.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.dependencies import orchestrator
from app.logging_config import get_logger
from app.mocks.member_data import MemberNotFoundError
from app.services.member_client import MemberServiceUnavailableError

logger = get_logger(__name__)

mcp = FastMCP(
    name="arrivia-travel-recommendations",
    # Mounted at "/mcp" by app.main; the app returned by
    # streamable_http_app() must itself serve at "/" or the effective path
    # becomes "/mcp/mcp".
    streamable_http_path="/",
    instructions=(
        "Tools for arrivia's AI Concierge: look up a member's loyalty tier "
        "and travel history, get partner-compliant personalized travel "
        "recommendations, and inspect the partner rules behind a "
        "recommendation. Read-only — these tools never modify member or "
        "booking data, so they're safe to call speculatively."
    ),
)


@mcp.tool()
async def get_member_travel_profile(member_id: str) -> dict:
    """Look up a member's loyalty tier, partner, and last 5 bookings.

    Args:
        member_id: The member's unique identifier (e.g. "m-1001").
    """
    logger.info("mcp_tool_called", extra={"extra_fields": {"tool": "get_member_travel_profile"}})
    try:
        profile = await orchestrator.get_member_profile(member_id)
    except MemberNotFoundError:
        return {"error": "member_not_found", "member_id": member_id}
    except MemberServiceUnavailableError:
        return {"error": "member_service_unavailable", "member_id": member_id}
    return profile.model_dump(mode="json")


@mcp.tool()
async def get_travel_recommendations(member_id: str, session_id: str | None = None) -> dict:
    """Generate personalized, partner-compliant travel recommendations for a member.

    Automatically applies the member's partner's rules (max recommendations
    per session, excluded categories such as cruises) — the caller never
    needs to know or pass those rules. If personalization data is
    unavailable, returns generic partner-compliant picks with
    `degraded: true` and a `degraded_reason` instead of failing outright, so
    the agent can be honest with the end user about reduced personalization.

    Args:
        member_id: The member's unique identifier (e.g. "m-1001").
        session_id: Optional caller-supplied identifier. Pass the same value
            across multiple tool calls in one concierge conversation so logs
            can be correlated by that session.
    """
    logger.info("mcp_tool_called", extra={"extra_fields": {"tool": "get_travel_recommendations"}})
    try:
        response = await orchestrator.get_recommendations(member_id, request_id=session_id)
    except MemberNotFoundError:
        return {"error": "member_not_found", "member_id": member_id}
    return response.model_dump(mode="json")


@mcp.tool()
async def list_partner_recommendation_rules(partner_id: str) -> dict:
    """Look up the active recommendation rules for a partner: max
    recommendations per session (null = unlimited) and excluded categories.
    Useful for an agent to explain *why* a recommendation list was capped or
    missing a category like cruises.

    Args:
        partner_id: The partner's unique identifier (e.g. "suntrust-rewards").
    """
    logger.info(
        "mcp_tool_called", extra={"extra_fields": {"tool": "list_partner_recommendation_rules"}}
    )
    config = await orchestrator.get_partner_rules(partner_id)
    return config.model_dump(mode="json")
