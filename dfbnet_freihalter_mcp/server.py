from __future__ import annotations

import asyncio
from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import DfbnetClient
from .config import load_config

mcp = FastMCP("dfbnet-freihalter")


def _client() -> DfbnetClient:
    return DfbnetClient(load_config())


@mcp.tool()
async def auth_status() -> dict[str, Any]:
    """Check local DFBNet token/session status without exposing token values."""
    return await _client().auth_status()


@mcp.tool()
def dry_run_full_day_exemption(date: str, reason: str = "PREVENTED", comment: str | None = None) -> dict[str, Any]:
    """Build the DFBNet payload for a full-day Freihalter without sending it. date format: YYYY-MM-DD."""
    return _client().dry_run_full_day_exemption(date, reason=reason, comment=comment)


@mcp.tool()
def dry_run_date_range_exemption(start_date: str, end_date: str, reason: str = "PREVENTED", comment: str | None = None) -> dict[str, Any]:
    """Build ONE DFBNet payload for a multi-day Freihalter from start_date through end_date inclusive. Dates: YYYY-MM-DD."""
    return _client().dry_run_date_range_exemption(start_date, end_date, reason=reason, comment=comment)


@mcp.tool()
def dry_run_delete_exemption(exemption_id: str) -> dict[str, Any]:
    """Build the DFBNet DELETE request for a Freihalter by id without sending it."""
    return _client().dry_run_delete_exemption(exemption_id)


@mcp.tool()
async def list_exemptions(from_iso: str = "2025-07-01T00:00:00.000Z") -> list[dict[str, Any]]:
    """List DFBNet Freihalter from an ISO timestamp, default current season start."""
    return await _client().list_exemptions(from_iso)


@mcp.tool()
async def check_exemption_conflict(from_iso: str, until_iso: str) -> list[dict[str, Any]]:
    """Check DFBNet conflicts for an exemption interval. Use dry_run first for full-day intervals."""
    return await _client().check_exemption_conflict(from_iso, until_iso)


@mcp.tool()
async def create_full_day_exemption(date: str, reason: str = "PREVENTED", comment: str | None = None, check_conflicts: bool = True, verify: bool = True) -> dict[str, Any]:
    """Create a full-day DFBNet Freihalter for YYYY-MM-DD, expect HTTP 204, then verify via list_exemptions."""
    return await _client().create_full_day_exemption(date, reason=reason, comment=comment, check_conflicts=check_conflicts, verify=verify)


@mcp.tool()
async def create_date_range_exemption(start_date: str, end_date: str, reason: str = "PREVENTED", comment: str | None = None, check_conflicts: bool = True, verify: bool = True) -> dict[str, Any]:
    """Create ONE multi-day DFBNet Freihalter from start_date through end_date inclusive. Prefer this over looping days for a period."""
    return await _client().create_date_range_exemption(start_date, end_date, reason=reason, comment=comment, check_conflicts=check_conflicts, verify=verify)


@mcp.tool()
async def delete_exemption(exemption_id: str, verify: bool = True) -> dict[str, Any]:
    """Delete a DFBNet Freihalter by its id. List exemptions first if you need the id."""
    return await _client().delete_exemption(exemption_id, verify=verify)


@mcp.tool()
async def create_exemption(from_iso: str, until_iso: str, reason: str = "PREVENTED", comment: str | None = None, verify: bool = True) -> dict[str, Any]:
    """Create a DFBNet Freihalter from explicit UTC/local ISO timestamps."""
    payload = {"from": from_iso, "until": until_iso, "reason": reason, "comment": comment}
    return await _client().create_exemption(payload, verify=verify)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
