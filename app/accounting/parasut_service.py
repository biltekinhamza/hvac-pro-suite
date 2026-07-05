from __future__ import annotations

from datetime import date, timedelta
import re
import unicodedata
from typing import Any

from app.accounting.parasut_client import ParasutClient, parasut_client
from app.config import settings
from app.ventilation.part_config import PARTS
from app.ventilation.part_description import part_measure_text


PART_PRODUCT_CODES = {
    "dikdortgen_kanal": "DIKDORTGEN_KANAL",
    "kare_dirsek": "KARE_DIRSEK",
    "kare_reduksiyon": "KARE_REDUKSIYON",
    "kare_es_1": "KARE_ES_1",
    "kare_es_2": "KARE_ES_2",
    "kare_pantolon": "KARE_PANTOLON",
    "kare_pantolon_2": "KARE_PANTOLON_2",
    "kare_istavroz": "KARE_ISTAVROZ",
    "kutu": "KUTU",
    "kare_kapak": "KARE_KAPAK",
    "spiro_boru": "SPIRO_BORU",
    "kareden_yuvarlaga": "KAREDEN_YUVARLAGA",
    "kortapa": "KORTAPA",
    "yuvarlak_dirsek": "YUVARLAK_DIRSEK",
    "yuvarlak_istavroz": "YUVARLAK_ISTAVROZ",
    "yuvarlak_mason": "YUVARLAK_MANSON",
    "yuvarlak_reduksiyon": "YUVARLAK_REDUKSIYON",
    "yuvarlak_te": "YUVARLAK_TE",
}


class ParasutService:
    def __init__(self, client: ParasutClient) -> None:
        self.client = client

    async def create_offer_from_quote(self, quote: dict[str, Any], items: list[dict[str, Any]]) -> str:
        contact_id = await self._find_or_create_contact(quote["customer_name"])
        details = []
        for item in items:
            product_id = await self._find_or_create_part_product(item["part_code"])
            description = part_measure_text(item["part_code"], item.get("inputs", {}))
            details.append({
                "type": "sales_offer_details",
                "attributes": {
                    "description": description or item["part_name"],
                    "quantity": item["quantity"],
                    "unit_price": item["unit_price"],
                    "vat_rate": settings.default_vat_rate,
                },
                "relationships": {
                    "product": {
                        "data": {"id": str(product_id), "type": "products"}
                    }
                },
            })

        today = date.today()
        due = today + timedelta(days=settings.default_offer_due_days)
        payload = {
            "data": {
                "type": "sales_offers",
                "attributes": {
                    "item_type": "sales_offer",
                    "issue_date": today.isoformat(),
                    "due_date": due.isoformat(),
                    "currency": settings.default_currency,
                    "description": f"Web teklif talebi #{quote['id']}",
                    "content": "Teklif geçerlilik süresi ve ödeme şartları için firma ile iletişime geçiniz.",
                    "order_no": f"WEB-{quote['id']}",
                    "order_date": today.isoformat(),
                },
                "relationships": {
                    "contact": {"data": {"id": str(contact_id), "type": "contacts"}},
                    "details": {"data": details},
                },
            }
        }
        response = await self.client.request("POST", "/sales_offers", json=payload)
        return str(response["data"]["id"])

    async def find_contact_by_id(self, contact_id: str) -> dict[str, Any] | None:
        try:
            response = await self.client.request("GET", f"/contacts/{contact_id}")
        except Exception:
            return None
        data = response.get("data")
        return self._contact_payload(data) if data else None

    async def find_contact_by_phone(self, phone: str, max_pages: int = 8) -> dict[str, Any] | None:
        target = _digits(phone)
        if not target:
            return None
        for page in range(1, max_pages + 1):
            response = await self.client.request(
                "GET",
                "/contacts",
                params={"filter[account_type]": "customer", "page[number]": page, "page[size]": 25},
            )
            for item in response.get("data", []):
                attrs = item.get("attributes", {})
                phone_digits = _digits(attrs.get("phone", ""))
                if phone_digits and (phone_digits.endswith(target[-10:]) or target.endswith(phone_digits[-10:])):
                    return self._contact_payload(item)
            meta = response.get("meta", {})
            current = int(meta.get("current_page", page) or page)
            total = int(meta.get("total_pages", page) or page)
            if current >= total:
                break
        return None

    async def find_contact_by_tax_and_title(self, tax_id: str, title: str) -> dict[str, Any] | None:
        tax = _digits(tax_id)
        if not tax:
            return None
        response = await self.client.request(
            "GET",
            "/contacts",
            params={"filter[tax_number]": tax, "filter[account_type]": "customer", "page[size]": 10},
        )
        expected = _normalize_title(title)
        for item in response.get("data", []):
            attrs = item.get("attributes", {})
            actual = _normalize_title(attrs.get("name", ""))
            if expected and (expected in actual or actual in expected or _title_similarity(expected, actual) >= 0.62):
                return self._contact_payload(item)
        return None

    def format_balance_message(self, contact: dict[str, Any]) -> str:
        balance = float(contact.get("trl_balance") or contact.get("balance") or 0)
        if balance > 0:
            direction = "borç"
        elif balance < 0:
            direction = "alacak"
        else:
            direction = "bakiye yok"
        amount = abs(balance)
        amount_text = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"Cari hesabınız bulundu.\n\nÜnvan: {contact['name']}\nBakiye: {amount_text} TL {direction}"

    def _contact_payload(self, item: dict[str, Any]) -> dict[str, Any]:
        attrs = item.get("attributes", {})
        return {
            "id": str(item.get("id")),
            "name": attrs.get("name") or "",
            "phone": attrs.get("phone") or "",
            "tax_number": attrs.get("tax_number") or "",
            "balance": attrs.get("balance") or 0,
            "trl_balance": attrs.get("trl_balance") or attrs.get("balance") or 0,
        }

    async def _find_or_create_contact(self, name: str) -> str:
        clean_name = (name or "Genel Müşteri").strip() or "Genel Müşteri"
        response = await self.client.request(
            "GET",
            "/contacts",
            params={"filter[name]": clean_name, "filter[account_type]": "customer", "page[size]": 1},
        )
        data = response.get("data", [])
        if data:
            return str(data[0]["id"])

        payload = {
            "data": {
                "type": "contacts",
                "attributes": {
                    "name": clean_name,
                    "account_type": "customer",
                    "contact_type": "company",
                },
            }
        }
        response = await self.client.request("POST", "/contacts", json=payload)
        return str(response["data"]["id"])

    async def _find_or_create_part_product(self, part_code: str) -> str:
        product_code = PART_PRODUCT_CODES[part_code]
        response = await self.client.request("GET", "/products", params={"filter[code]": product_code, "page[size]": 1})
        data = response.get("data", [])
        if data:
            return str(data[0]["id"])

        part = PARTS[part_code]
        payload = {
            "data": {
                "type": "products",
                "attributes": {
                    "name": part["title"],
                    "code": product_code,
                    "vat_rate": settings.default_vat_rate,
                    "unit": "Adet",
                    "currency": settings.default_currency,
                    "list_price": 0,
                },
            }
        }
        response = await self.client.request("POST", "/products", json=payload)
        return str(response["data"]["id"])


parasut_service = ParasutService(parasut_client)


def _digits(value: object) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _normalize_title(value: object) -> str:
    text = str(value or "").lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("ı", "i")
    text = re.sub(r"\b(ltd|limited|sti|şti|aş|as|anonim|sirketi|şirketi|tic|san)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _title_similarity(left: str, right: str) -> float:
    left_set = set(left.split())
    right_set = set(right.split())
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)
