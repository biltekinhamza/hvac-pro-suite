from __future__ import annotations

import hashlib
import hmac
import logging
import re
import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.accounting.parasut_service import parasut_service
from app.repository import repository
from app.whatsapp.client import whatsapp_client


router = APIRouter(prefix="/webhook", tags=["whatsapp"])
logger = logging.getLogger(__name__)


@router.get("")
@router.get("/whatsapp")
def verify_webhook(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
) -> PlainTextResponse:
    if not settings.whatsapp_verify_token:
        raise HTTPException(status_code=500, detail="WHATSAPP_VERIFY_TOKEN tanımlı değil.")
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Webhook doğrulama tokeni hatalı.")


@router.post("")
@router.post("/whatsapp")
async def receive_webhook(request: Request) -> dict[str, object]:
    body = await request.body()
    _verify_signature(request, body)
    payload = await request.json()
    messages = _extract_messages(payload)
    for message in messages:
        sender = message.get("from")
        text = (message.get("text") or {}).get("body", "").strip()
        if not sender or not text:
            continue
        reply = await _build_auto_reply(sender, text)
        try:
            if reply["type"] == "cta_url":
                try:
                    await whatsapp_client.send_cta_url(sender, reply["body"], reply["button_text"], reply["url"])
                except httpx.HTTPStatusError:
                    await whatsapp_client.send_text(sender, f"{reply['body']}\n{reply['url']}")
            else:
                await whatsapp_client.send_text(sender, reply["body"])
        except ValueError:
            # Local development can receive webhook payloads before WhatsApp credentials are set.
            pass
        except httpx.HTTPError as exc:
            logger.warning("WhatsApp mesaj gönderim hatası: %s", _http_error_detail(exc))
    return {"ok": True, "messages": len(messages)}


def _extract_messages(payload: dict) -> list[dict]:
    messages: list[dict] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages.extend(value.get("messages", []))
    return messages


def _http_error_detail(exc: httpx.HTTPError) -> str:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
        return exc.response.text[:1000]
    return str(exc)


def _verify_signature(request: Request, body: bytes) -> None:
    if not settings.whatsapp_app_secret:
        return

    signature = request.headers.get("x-hub-signature-256", "")
    if not signature:
        if settings.app_env == "production":
            raise HTTPException(status_code=403, detail="Webhook imzası eksik.")
        return

    expected = "sha256=" + hmac.new(
        settings.whatsapp_app_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=403, detail="Webhook imzası geçersiz.")


async def _build_auto_reply(sender: str, text: str) -> dict[str, str]:
    lowered = text.lower()
    session = repository.get_or_create_customer_session(sender)

    try:
        if session["pending_action"] == "verify_cari":
            return {"type": "text", "body": await _handle_cari_verification(session, text)}

        if _is_balance_request(lowered):
            return {"type": "text", "body": await _handle_balance_request(session, sender)}
    except (ValueError, httpx.HTTPError) as exc:
        logger.warning("Cari sorgu hatası: %s", _http_error_detail(exc) if isinstance(exc, httpx.HTTPError) else str(exc))
        return {
            "type": "text",
            "body": "Cari bilgisi şu anda kontrol edilemiyor. Lütfen daha sonra tekrar deneyiniz veya firmamızla iletişime geçiniz.",
        }

    if any(word in lowered for word in ["sipariş", "siparis", "sipari", "teklif"]):
        base_url = settings.public_base_url.rstrip("/") or "http://127.0.0.1:8010"
        order_url = f"{base_url}/?s={session['session_token']}"
        return {
            "type": "cta_url",
            "body": "Sipariş/teklif talebiniz için parça seçimi ve ölçü giriş formunu açabilirsiniz.",
            "button_text": "Sipariş Formunu Aç",
            "url": order_url,
        }
    return {"type": "text", "body": "Merhaba, Tavsan Makina'ya hoş geldiniz. Bakiye sorgusu veya sipariş/teklif talebi için nasıl yardımcı olabiliriz?"}


def _is_balance_request(text: str) -> bool:
    return bool(re.search(r"\b(bakiye|borç|borc|borcum|borcumuz|cari)\b", text))


async def _handle_balance_request(session, sender: str) -> str:
    if session["parasut_contact_id"]:
        contact = await parasut_service.find_contact_by_id(session["parasut_contact_id"])
        if contact:
            return parasut_service.format_balance_message(contact)

    contact = await parasut_service.find_contact_by_phone(sender)
    if contact:
        repository.set_customer_session_contact(session["id"], contact["id"], contact["name"])
        return parasut_service.format_balance_message(contact)

    repository.set_customer_session_pending_action(session["id"], "verify_cari")
    return (
        "Cari hesabınızı WhatsApp numaranızla bulamadım.\n\n"
        "Lütfen doğrulama için Vergi No / T.C. Kimlik No ve ünvanınızı yazınız.\n"
        "Örnek:\nVergi No: 1234567890\nÜnvan: ABC İnşaat Ltd. Şti."
    )


async def _handle_cari_verification(session, text: str) -> str:
    parsed = _parse_tax_and_title(text)
    if not parsed:
        return (
            "Bilgileri okuyamadım. Lütfen şu formatta yazınız:\n"
            "Vergi No: 1234567890\nÜnvan: ABC İnşaat Ltd. Şti."
        )

    tax_id, title = parsed
    contact = await parasut_service.find_contact_by_tax_and_title(tax_id, title)
    if not contact:
        return "Bu Vergi/T.C. No ve ünvan ile cari hesabı doğrulayamadım. Lütfen bilgileri kontrol edip tekrar yazınız."

    repository.set_customer_session_contact(session["id"], contact["id"], contact["name"])
    return parasut_service.format_balance_message(contact)


def _parse_tax_and_title(text: str) -> tuple[str, str] | None:
    tax_match = re.search(r"\b\d{10,11}\b", text)
    if not tax_match:
        return None
    tax_id = tax_match.group(0)
    title = text.replace(tax_id, " ")
    title = re.sub(r"(?i)(vergi|vkn|tckn|tc|no|numara|ünvan|unvan|firma|ad[ıi])\s*[:：-]?", " ", title)
    title = re.sub(r"\s+", " ", title).strip(" .:-")
    if len(title) < 3:
        return None
    return tax_id, title
