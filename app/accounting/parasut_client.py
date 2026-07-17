from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from app.config import settings


class ParasutClient:
    def __init__(self) -> None:
        self.base_url = "https://api.parasut.com"
        self.api_url = f"{self.base_url}/v4/{settings.parasut_company_id}"
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at = 0.0

    def is_configured(self) -> bool:
        return all([
            settings.parasut_client_id,
            settings.parasut_client_secret,
            settings.parasut_username,
            settings.parasut_password,
            settings.parasut_company_id,
        ])

    async def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if not self.is_configured():
            raise ValueError("Paraşüt .env bilgileri eksik.")

        token = await self._token()
        headers = kwargs.pop("headers", {})
        headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.api+json",
        })
        async with httpx.AsyncClient(timeout=30) as client:
            for attempt in range(3):
                response = await client.request(method, f"{self.api_url}{path}", headers=headers, **kwargs)
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "5"))
                    await asyncio.sleep(retry_after)
                    continue
                if response.status_code == 401 and self._refresh_token:
                    await self._refresh_access_token()
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    response = await client.request(method, f"{self.api_url}{path}", headers=headers, **kwargs)
                response.raise_for_status()
                break
            if response.status_code == 204 or not response.content:
                return {}
            return response.json()

    async def _token(self) -> str:
        if self._access_token and time.time() < self._expires_at - 60:
            return self._access_token
        if self._refresh_token:
            try:
                await self._refresh_access_token()
                return self._access_token or ""
            except httpx.HTTPError:
                self._refresh_token = None
        await self._password_access_token()
        return self._access_token or ""

    async def _password_access_token(self) -> None:
        data = {
            "grant_type": "password",
            "client_id": settings.parasut_client_id,
            "client_secret": settings.parasut_client_secret,
            "username": settings.parasut_username,
            "password": settings.parasut_password,
            "redirect_uri": settings.parasut_redirect_uri,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{self.base_url}/oauth/token", data=data)
            response.raise_for_status()
        payload = response.json()
        self._access_token = payload["access_token"]
        self._refresh_token = payload.get("refresh_token")
        self._expires_at = time.time() + int(payload.get("expires_in", 7200))

    async def _refresh_access_token(self) -> None:
        data = {
            "grant_type": "refresh_token",
            "client_id": settings.parasut_client_id,
            "client_secret": settings.parasut_client_secret,
            "refresh_token": self._refresh_token,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{self.base_url}/oauth/token", data=data)
            response.raise_for_status()
        payload = response.json()
        self._access_token = payload["access_token"]
        self._refresh_token = payload.get("refresh_token")
        self._expires_at = time.time() + int(payload.get("expires_in", 7200))


parasut_client = ParasutClient()
