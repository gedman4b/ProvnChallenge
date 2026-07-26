"""Integration tests for the MCP tool layer — exercises tool discovery and
invocation through an in-process MCP session (no HTTP transport needed),
proving the tools are correctly registered and produce the same
rule-enforced output as the REST layer, since both call the same
orchestrator."""

from __future__ import annotations

import json

from mcp.shared.memory import create_connected_server_and_client_session

from app.mcp_server import mcp


async def test_tools_are_discoverable():
    async with create_connected_server_and_client_session(mcp) as session:
        result = await session.list_tools()
        names = {t.name for t in result.tools}

    assert names == {
        "get_member_travel_profile",
        "get_travel_recommendations",
        "list_partner_recommendation_rules",
    }


async def test_get_member_travel_profile_returns_known_member():
    async with create_connected_server_and_client_session(mcp) as session:
        result = await session.call_tool("get_member_travel_profile", {"member_id": "m-1001"})

    payload = json.loads(result.content[0].text)
    assert payload["member_id"] == "m-1001"
    assert payload["partner_id"] == "suntrust-rewards"


async def test_get_member_travel_profile_reports_not_found_without_raising():
    async with create_connected_server_and_client_session(mcp) as session:
        result = await session.call_tool("get_member_travel_profile", {"member_id": "nope"})

    payload = json.loads(result.content[0].text)
    assert payload["error"] == "member_not_found"


async def test_get_travel_recommendations_enforces_partner_cap():
    # suntrust-rewards caps recommendations at 3 (see app/mocks/partner_configs.py)
    async with create_connected_server_and_client_session(mcp) as session:
        result = await session.call_tool("get_travel_recommendations", {"member_id": "m-1001"})

    payload = json.loads(result.content[0].text)
    assert len(payload["recommendations"]) <= 3
    assert payload["applied_rules"]["max_recommendations"] == 3


async def test_get_travel_recommendations_excludes_cruise_for_globalfirst():
    async with create_connected_server_and_client_session(mcp) as session:
        result = await session.call_tool("get_travel_recommendations", {"member_id": "m-1003"})

    payload = json.loads(result.content[0].text)
    categories = {rec["category"] for rec in payload["recommendations"]}
    assert "cruise" not in categories


async def test_list_partner_recommendation_rules_exposes_cap_and_exclusions():
    async with create_connected_server_and_client_session(mcp) as session:
        result = await session.call_tool(
            "list_partner_recommendation_rules", {"partner_id": "meridian-points"}
        )

    payload = json.loads(result.content[0].text)
    assert payload["max_recommendations"] == 1
    assert "cruise" in payload["excluded_categories"]
