#!/usr/bin/env python3
"""End-to-end smoke test against the live MCP endpoint (not in-process).

Run the server first:
    uvicorn app.main:app --port 8000

Then in another shell:
    python scripts/mcp_smoke_test.py [base_url]   # default http://localhost:8000/mcp

Demonstrates tool discovery plus rule enforcement across partners with
different configs: a capped partner, an unlimited partner that excludes
cruises, and a partner_id absent from the config service (fail-safe
fallback).
"""

from __future__ import annotations

import asyncio
import json
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

SCENARIOS = [
    ("m-1001", "suntrust-rewards: capped at 3 recommendations"),
    ("m-1003", "globalfirst-travel: unlimited, but cruise offers excluded"),
    ("m-1005", "meridian-points: capped at 1, cruise + package excluded"),
    ("m-1007", "unregistered-partner-x: not in partner config service -> strict fail-safe fallback"),
    ("m-1008", "suntrust-rewards, brand-new member with no travel history (cold start)"),
    ("does-not-exist", "unknown member -> clean not-found error, no crash"),
]


async def main(base_url: str) -> None:
    async with streamablehttp_client(base_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print(f"Discovered {len(tools.tools)} tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description.splitlines()[0]}")
            print()

            for member_id, label in SCENARIOS:
                print(f"--- {label} ({member_id}) ---")
                result = await session.call_tool(
                    "get_travel_recommendations", {"member_id": member_id}
                )
                payload = json.loads(result.content[0].text)
                if "error" in payload:
                    print(f"  error: {payload['error']}")
                else:
                    rules = payload["applied_rules"]
                    print(
                        f"  partner={payload['partner_id']} "
                        f"degraded={payload['degraded']} "
                        f"recommendations={len(payload['recommendations'])} "
                        f"cap={rules['max_recommendations']} "
                        f"excluded={rules['excluded_categories']}"
                    )
                    for rec in payload["recommendations"]:
                        print(f"    - [{rec['category']}] {rec['title']} — {rec['reason']}")
                print()


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/mcp"
    asyncio.run(main(url))
