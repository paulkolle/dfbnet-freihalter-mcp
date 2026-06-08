from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from .auth import TokenManager, summarize_token
from .config import DfbnetConfig
from .dates import date_range_payload, full_day_payload, local_day_match


class DfbnetClient:
    def __init__(self, config: DfbnetConfig):
        self.config = config
        self.tokens = TokenManager(config)

    async def _headers(self) -> dict[str, str]:
        token = await self.tokens.get_valid_access_token()
        return {
            "accept": "application/json",
            "accept-language": "de-DE",
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
            "origin": self.config.origin,
            "referer": f"{self.config.origin}/",
            "user-agent": "Mozilla/5.0 DFBNet-Freihalter-MCP/0.1",
        }

    async def auth_status(self) -> dict[str, Any]:
        bundle = self.tokens.load()
        return {
            "token_state_path": str(self.config.token_state_path),
            "token_state_exists": self.config.token_state_path.exists(),
            "storage_state_path": str(self.config.storage_state_path),
            "storage_state_exists": self.config.storage_state_path.exists(),
            "origin": self.config.origin,
            "access_token": summarize_token(bundle.access_token),
            "refresh_token_present": bool(bundle.refresh_token),
            "expires_in_seconds": bundle.expires_in_seconds(),
        }

    async def list_exemptions(self, from_iso: str | None = None) -> list[dict[str, Any]]:
        from_iso = from_iso or self.config.verify_after_create_from
        url = f"{self.config.api_base_url}/referee/{self.config.referee_id}/exemption?from={quote(from_iso, safe='')}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=await self._headers())
        if resp.status_code >= 400:
            raise RuntimeError(f"list_exemptions failed HTTP {resp.status_code}: {resp.text[:500]}")
        return resp.json()

    async def check_exemption_conflict(self, from_iso: str, until_iso: str) -> list[dict[str, Any]]:
        url = f"{self.config.api_base_url}/referee/{self.config.referee_id}/exemption-conflict?from={quote(from_iso, safe='')}&until={quote(until_iso, safe='')}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=await self._headers())
        if resp.status_code >= 400:
            raise RuntimeError(f"check_exemption_conflict failed HTTP {resp.status_code}: {resp.text[:500]}")
        return resp.json()

    async def create_exemption(self, payload: dict[str, Any], verify: bool = True) -> dict[str, Any]:
        url = f"{self.config.api_base_url}/referee/{self.config.referee_id}/exemption"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=await self._headers(), json=payload)
        if resp.status_code != 204:
            raise RuntimeError(f"create_exemption expected HTTP 204, got {resp.status_code}: {resp.text[:500]}")
        result: dict[str, Any] = {"created": True, "status_code": resp.status_code, "payload": payload}
        if verify:
            exemptions = await self.list_exemptions(self.config.verify_after_create_from)
            matches = [x for x in exemptions if x.get("reason") == payload.get("reason") and x.get("comment") == payload.get("comment") and _rough_same_interval(x, payload)]
            result["verified"] = bool(matches)
            result["matches"] = matches
            result["exemptions_count"] = len(exemptions)
        return result

    async def create_date_range_exemption(self, start_date: str, end_date: str, reason: str = "PREVENTED", comment: str | None = None, check_conflicts: bool = True, verify: bool = True) -> dict[str, Any]:
        """Create one DFBNet NORMAL exemption spanning start_date 00:00 through end_date 23:59 local time."""
        payload = date_range_payload(start_date, end_date, self.config.timezone, reason=reason, comment=comment)
        result: dict[str, Any] = {"start_date": start_date, "end_date": end_date, "payload": payload}
        if check_conflicts:
            result["conflicts"] = await self.check_exemption_conflict(payload["from"], payload["until"])
        create_result = await self.create_exemption(payload, verify=verify)
        result.update(create_result)
        return result

    async def create_full_day_exemption(self, day: str, reason: str = "PREVENTED", comment: str | None = None, check_conflicts: bool = True, verify: bool = True) -> dict[str, Any]:
        payload = full_day_payload(day, self.config.timezone, reason=reason, comment=comment)
        result: dict[str, Any] = {"day": day, "payload": payload}
        if check_conflicts:
            result["conflicts"] = await self.check_exemption_conflict(payload["from"], payload["until"])
        create_result = await self.create_exemption(payload, verify=verify)
        result.update(create_result)
        return result

    def dry_run_date_range_exemption(self, start_date: str, end_date: str, reason: str = "PREVENTED", comment: str | None = None) -> dict[str, Any]:
        return {
            "start_date": start_date,
            "end_date": end_date,
            "timezone": self.config.timezone,
            "referee_id": self.config.referee_id,
            "url": f"{self.config.api_base_url}/referee/{self.config.referee_id}/exemption",
            "payload": date_range_payload(start_date, end_date, self.config.timezone, reason=reason, comment=comment),
        }

    def dry_run_full_day_exemption(self, day: str, reason: str = "PREVENTED", comment: str | None = None) -> dict[str, Any]:
        return {
            "day": day,
            "timezone": self.config.timezone,
            "referee_id": self.config.referee_id,
            "url": f"{self.config.api_base_url}/referee/{self.config.referee_id}/exemption",
            "payload": full_day_payload(day, self.config.timezone, reason=reason, comment=comment),
        }

    def dry_run_delete_exemption(self, exemption_id: str) -> dict[str, Any]:
        return {
            "method": "DELETE",
            "url": f"{self.config.api_base_url}/referee/{self.config.referee_id}/exemption/{exemption_id}",
            "exemption_id": exemption_id,
        }

    async def delete_exemption(self, exemption_id: str, verify: bool = True) -> dict[str, Any]:
        url = self.dry_run_delete_exemption(exemption_id)["url"]
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.delete(url, headers=await self._headers())
        if resp.status_code != 204:
            raise RuntimeError(f"delete_exemption expected HTTP 204, got {resp.status_code}: {resp.text[:500]}")
        result: dict[str, Any] = {"deleted": True, "status_code": resp.status_code, "exemption_id": exemption_id}
        if verify:
            exemptions = await self.list_exemptions(self.config.verify_after_create_from)
            result["verified"] = not any(x.get("id") == exemption_id for x in exemptions)
            result["exemptions_count"] = len(exemptions)
        return result


def _rough_same_interval(entry: dict[str, Any], payload: dict[str, Any]) -> bool:
    # API returns local offset strings, create payload uses UTC Z. Compare by local day shape if exact strings differ.
    from datetime import datetime
    try:
        ef = datetime.fromisoformat(str(entry["from"]).replace("Z", "+00:00")).timestamp()
        eu = datetime.fromisoformat(str(entry["until"]).replace("Z", "+00:00")).timestamp()
        pf = datetime.fromisoformat(str(payload["from"]).replace("Z", "+00:00")).timestamp()
        pu = datetime.fromisoformat(str(payload["until"]).replace("Z", "+00:00")).timestamp()
        return abs(ef - pf) < 1 and abs(eu - pu) < 1
    except Exception:
        return False
