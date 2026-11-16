"""IPARK cloud 2.0 protocol observed in the official 1.5.4 app."""
from __future__ import annotations

import asyncio
import json
from urllib.parse import quote, urlsplit

import aiohttp

CENTER_URL = "https://center.hdc-smart.com"
# Public application identifier shipped in the official client, not a household token.
APP_API_KEY = "ZXlKaGJHY2lPaUpJVXpJMU5pSXNJblI1Y0NJNklrcFhWQ0o5LmV5SnpaV055WlhRaU9pSXhNak0wTlRZM09Ea3dJaXdpYm1GdFpTSTZJbk50WVhKMGFHOXRaU0o5Ljk5YjBNYWtXUkNaSzhhVExkOW1XOFlXanR5VnNpd2k5NmNlWjNkYzZzWFk"


class CloudError(Exception):
    """A sanitized cloud error, safe to show without response bodies."""


def validate_session(value: object) -> dict:
    """Refuse malformed sessions before sending household credentials."""
    if not isinstance(value, dict) or not isinstance(value.get("access-token"), str) or not value["access-token"]:
        raise CloudError("invalid_response")
    url = value.get("url")
    if not isinstance(url, str):
        raise CloudError("invalid_response")
    try:
        parts = urlsplit(url)
        valid = (parts.scheme in ("http", "https") and parts.hostname and parts.port != 0
                 and not parts.username and not parts.password and not parts.query
                 and not parts.fragment and parts.path in ("", "/")
                 and not any(c.isspace() for c in url))
    except ValueError as exc:
        raise CloudError("invalid_response") from exc
    if not valid:
        raise CloudError("invalid_response")
    return {**value, "url": url.rstrip("/")}


def elevator_support(site: object, category: str = "elevator") -> bool | None:
    """True/False only for a valid capability list; missing data is unknown."""
    if not isinstance(site, dict):
        return None
    additional = site.get("additional")
    if isinstance(additional, str):
        try:
            additional = json.loads(additional)
        except (ValueError, TypeError):
            return None
    if not isinstance(additional, list) or any(not isinstance(v, dict) for v in additional):
        return None
    return any(v.get("category") == category for v in additional)


def onepass_support(site: object) -> bool | None:
    """Read the same capability list for lobby access."""
    return elevator_support(site, "onepass")


class CloudAPI:
    """Use a caller-owned session; never retry side-effecting requests."""

    def __init__(self, session, device_uuid: str = ""):
        self.session = session
        self.uuid = device_uuid

    async def _request(self, method: str, url: str, headers: dict, **kwargs):
        try:
            async with self.session.request(
                method, url, headers={"Content-Type": "application/json", **headers},
                timeout=aiohttp.ClientTimeout(total=15), allow_redirects=False, **kwargs,
            ) as response:
                if response.status in (401, 403):
                    raise CloudError("auth_failed")
                if not 200 <= response.status < 300:
                    raise CloudError("request_failed")
                body = await response.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            raise CloudError("network_error") from exc
        if isinstance(body, dict) and (body.get("err") or body.get("result") in ("fail", "error")):
            raise CloudError("request_failed")
        return body

    async def _central(self, method: str, path: str, **kwargs):
        return await self._request(method, CENTER_URL + path,
                                   {"X-API-KEY": APP_API_KEY, "Authorization": self.uuid}, **kwargs)

    async def complexes(self) -> list[dict]:
        body = await self._central("GET", "/v3/auth/valley")
        if not isinstance(body, list):
            raise CloudError("invalid_response")
        rows = [v for v in body if isinstance(v, dict) and v.get("code") and v.get("name")]
        if not rows:
            raise CloudError("invalid_response")
        return rows

    async def register(self, site: str, dong: str, ho: str, alias: str) -> str:
        body = await self._central("POST", "/v3/auth/registration", json={
            "type": "homedev", "site": site, "identifier": f"{dong}/{ho}", "alias": alias,
        })
        if not isinstance(body, dict) or not isinstance(body.get("transaction"), str) or not body["transaction"]:
            raise CloudError("invalid_response")
        return body["transaction"]

    async def verify(self, transaction: str, password: str) -> None:
        body = await self._central("POST", "/v3/auth/verify", json={
            "transaction": transaction, "password": password,
        })
        if not isinstance(body, dict):
            raise CloudError("invalid_response")

    async def login(self) -> dict:
        return validate_session(await self._central("POST", "/v3/auth/login", data="V2"))

    async def site_info(self, session: dict):
        session = validate_session(session)
        return await self._request("GET", session["url"] + "/v2/api/refs/site",
                                   {"access-token": session["access-token"]})

    async def call_elevator(self, session: dict, direction: str) -> None:
        if direction not in ("up", "down"):
            raise ValueError("Unsupported elevator direction")
        session = validate_session(session)
        result = await self._request(
            "POST", session["url"] + f"/v2/api/elevator/{direction}",
            {"access-token": session["access-token"]}, data=direction,
        )
        if not isinstance(result, dict) or result.get("result") != "ok":
            raise CloudError("request_failed")

    async def doors(self, session: dict) -> list[dict]:
        session = validate_session(session)
        body = await self._request("GET", session["url"] + "/v2/api/onepass/doors",
                                   {"access-token": session["access-token"]})
        if not isinstance(body, list):
            raise CloudError("invalid_response")
        doors = []
        seen = set()
        for row in body:
            if (not isinstance(row, dict) or type(row.get("id")) not in (str, int)
                    or not str(row["id"]).strip() or str(row["id"]) in (".", "..")
                    or not isinstance(row.get("lobby_name"), str) or not row["lobby_name"].strip()):
                raise CloudError("invalid_response")
            door_id = str(row["id"])
            if door_id in seen:
                raise CloudError("invalid_response")
            seen.add(door_id)
            doors.append({"id": door_id, "lobby_name": row["lobby_name"].strip()})
        return doors

    async def open_door(self, session: dict, door_id: str) -> None:
        session = validate_session(session)
        if (not isinstance(door_id, str) or not door_id.strip() or door_id in (".", "..")
                or not isinstance(session.get("alias"), str) or not session["alias"].strip()):
            raise CloudError("invalid_response")
        result = await self._request(
            "POST", session["url"] + f"/v2/api/onepass/doors/{quote(door_id, safe='')}/apply",
            {"access-token": session["access-token"]},
            json={"appname": "스마트홈2.0", "alias": session["alias"]},
        )
        if not isinstance(result, dict) or result.get("result") != "ok":
            raise CloudError("request_failed")
