from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


class WhatsAppClient:
    def __init__(self) -> None:
        self.base_url = "https://graph.facebook.com/v20.0"

    def is_configured(self) -> bool:
        return bool(settings.whatsapp_access_token and settings.whatsapp_phone_number_id)

    async def send_text(self, to: str, text: str) -> dict[str, Any]:
        if not self.is_configured():
            raise ValueError("WhatsApp .env bilgileri eksik.")

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
        headers = {
            "Authorization": f"Bearer {settings.whatsapp_access_token}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/{settings.whatsapp_phone_number_id}/messages"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def send_cta_url(self, to: str, body: str, button_text: str, url_value: str) -> dict[str, Any]:
        if not self.is_configured():
            raise ValueError("WhatsApp .env bilgileri eksik.")

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "cta_url",
                "body": {"text": body},
                "action": {
                    "name": "cta_url",
                    "parameters": {
                        "display_text": button_text,
                        "url": url_value,
                    },
                },
            },
        }
        headers = {
            "Authorization": f"Bearer {settings.whatsapp_access_token}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/{settings.whatsapp_phone_number_id}/messages"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()


whatsapp_client = WhatsAppClient()
