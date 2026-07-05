from __future__ import annotations

import logging
import secrets

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from app.accounting.parasut_service import parasut_service
from app.config import TEMPLATE_DIR, settings
from app.models import CalculateRequest, CartItemRequest, MaterialCostUpdateRequest, QuoteCreateRequest
from app.repository import repository
from app.utils import loads_json
from app.ventilation.engine import CostEngine
from app.ventilation.part_config import PARTS
from app.ventilation.service import ventilation_service
from app.whatsapp.client import whatsapp_client


router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
engine = CostEngine(repository)
logger = logging.getLogger(__name__)
security = HTTPBasic(auto_error=False)


def require_admin(credentials: HTTPBasicCredentials | None = Depends(security)) -> str:
    if not settings.admin_password:
        return "admin"
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin girisi gerekli.",
            headers={"WWW-Authenticate": "Basic"},
        )

    username_ok = secrets.compare_digest(credentials.username, settings.admin_username)
    password_ok = secrets.compare_digest(credentials.password, settings.admin_password)
    if username_ok and password_ok:
        return credentials.username
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Admin girisi gerekli.",
        headers={"WWW-Authenticate": "Basic"},
    )


@router.get("/", response_class=HTMLResponse)
def order_page(request: Request):
    return templates.TemplateResponse("order.html", {"request": request, "session_token": request.query_params.get("s", "")})


@router.get("/admin/quotes", response_class=HTMLResponse)
def admin_quotes_page(request: Request, _admin: str = Depends(require_admin)):
    return templates.TemplateResponse("admin_quotes.html", {"request": request})


@router.get("/admin/materials", response_class=HTMLResponse)
def admin_materials_page(request: Request, _admin: str = Depends(require_admin)):
    return templates.TemplateResponse("admin_materials.html", {"request": request})


@router.get("/api/parts")
def get_parts() -> dict:
    return {"items": ventilation_service.parts()}


@router.get("/api/admin/quotes")
def list_admin_quotes(_admin: str = Depends(require_admin)) -> dict:
    return {"items": [repository.serialize_quote(row) for row in repository.list_quotes()]}


@router.get("/api/admin/materials")
def list_admin_materials(_admin: str = Depends(require_admin)) -> dict:
    return {"items": [_serialize_material_option(row) for row in repository.list_material_options()]}


@router.post("/api/admin/materials/{option_id}")
def update_admin_material(option_id: int, payload: MaterialCostUpdateRequest, _admin: str = Depends(require_admin)) -> dict:
    try:
        row = repository.update_material_option_cost(option_id, payload.average_unit_cost)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "item": _serialize_material_option(row)}


@router.get("/api/admin/quotes/{quote_id}")
def get_admin_quote(quote_id: int, _admin: str = Depends(require_admin)) -> dict:
    try:
        quote, items = repository.get_quote(quote_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "quote": repository.serialize_quote(quote),
        "items": [repository.serialize_quote_item(row) for row in items],
    }


@router.post("/api/admin/quotes/{quote_id}/profit")
async def apply_admin_quote_profit(quote_id: int, request: Request, _admin: str = Depends(require_admin)) -> dict:
    payload = await request.json()
    try:
        repository.apply_quote_profit_rate(quote_id, payload.get("profit_rate", 0))
        quote, items = repository.get_quote(quote_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "ok": True,
        "quote": repository.serialize_quote(quote),
        "items": [repository.serialize_quote_item(row) for row in items],
    }


@router.post("/api/admin/quotes/{quote_id}/send-to-parasut")
async def send_admin_quote_to_parasut(quote_id: int, _admin: str = Depends(require_admin)) -> dict:
    try:
        quote_row, item_rows = repository.get_quote(quote_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    quote = repository.serialize_quote(quote_row)
    if quote.get("parasut_offer_id"):
        return {"ok": True, "parasut_offer_id": quote["parasut_offer_id"], "already_sent": True}

    items = [repository.serialize_quote_item(row) for row in item_rows]
    if not items:
        raise HTTPException(status_code=400, detail="Teklif kalemi yok.")

    try:
        parasut_offer_id = await parasut_service.create_offer_from_quote(quote, items)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:1000] if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"Paraşüt API hatası: {detail}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Paraşüt bağlantı hatası: {exc}") from exc

    repository.mark_quote_sent_to_parasut(quote_id, parasut_offer_id)
    return {"ok": True, "parasut_offer_id": parasut_offer_id, "already_sent": False}


@router.post("/api/calculate")
def calculate(payload: CalculateRequest) -> dict:
    inputs = _normalize_inputs(payload.inputs, payload.profit_rate)
    try:
        result = engine.calculate(payload.part_code, inputs)
        sale = engine.calculate_sale(result, payload.profit_rate, payload.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"result": result, "sale": sale}


@router.post("/api/cart/items")
def add_cart_item(payload: CartItemRequest) -> dict:
    inputs = _normalize_inputs(payload.inputs, payload.profit_rate)
    try:
        result = engine.calculate(payload.part_code, inputs)
        sale = engine.calculate_sale(result, payload.profit_rate, payload.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    item_id = repository.add_cart_item(payload.part_code, inputs, payload.quantity)
    return {"ok": True, "id": item_id, "result": result, "sale": sale, "cart": _cart_payload()}


@router.get("/api/cart")
def get_cart() -> dict:
    return _cart_payload()


@router.post("/api/quotes")
async def create_quote(payload: QuoteCreateRequest) -> dict:
    rows = repository.list_cart_items()
    if not rows:
        raise HTTPException(status_code=400, detail="Sepet boş.")

    prepared = []
    for row in rows:
        inputs = loads_json(row["inputs_json"], {})
        result = engine.calculate(row["part_code"], inputs)
        sale = engine.calculate_sale(result, inputs.get("profit_rate", "0"), row["quantity"])
        prepared.append({
            "part_code": row["part_code"],
            "part_name": PARTS[row["part_code"]]["title"],
            "quantity": row["quantity"],
            "unit_cost": sale["unit_cost"],
            "unit_price": sale["unit_price"],
            "line_total": sale["line_total"],
            "cut_area_m2": result["kesilen_m2"],
            "weight_kg": result["kg"],
            "inputs": inputs,
            "result": result,
        })
    quote_id = repository.create_quote(payload.customer_name, payload.shipping_amount, prepared)
    await _notify_new_quote(quote_id, payload.customer_name, prepared)
    return {"ok": True, "quote_id": quote_id}


def _normalize_inputs(inputs: dict[str, object], profit_rate: float) -> dict[str, object]:
    data = dict(inputs)
    data.setdefault("sac_kalinlik_mm", "0.60")
    data.setdefault("sac_ozellik_id", "")
    data.setdefault("flans_ekle", False)
    data.setdefault("flans_ozellik_id", "")
    data.setdefault("conta_ekle", False)
    data.setdefault("conta_ozellik_id", "")
    data.setdefault("vida_ekle", False)
    data.setdefault("vida_ozellik_id", "")
    data.setdefault("izolasyon_ozellik_id", "")
    data.setdefault("boya_ekle", False)
    data.setdefault("boya_birim_fiyat", "0")
    data["profit_rate"] = str(profit_rate)
    return data


def _cart_payload() -> dict:
    rows = repository.list_cart_items()
    items = []
    total = 0.0
    for row in rows:
        inputs = loads_json(row["inputs_json"], {})
        result = engine.calculate(row["part_code"], inputs)
        sale = engine.calculate_sale(result, inputs.get("profit_rate", "0"), row["quantity"])
        line_total = float(sale["line_total"])
        total += line_total
        items.append({
            "id": row["id"],
            "part_code": row["part_code"],
            "part_name": PARTS[row["part_code"]]["title"],
            "quantity": row["quantity"],
            "inputs": inputs,
            "result": result,
            "sale": sale,
            "line_total": line_total,
        })
    return {"items": items, "total": round(total, 2)}


def _serialize_material_option(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "option_name": row["option_name"],
        "unit": row["unit"],
        "quantity": float(row["quantity"] or 0),
        "average_unit_cost": float(row["average_unit_cost"] or 0),
    }


async def _notify_new_quote(quote_id: int, customer_name: str, items: list[dict]) -> None:
    phones = _notify_phones()
    if not phones:
        return

    base_url = settings.public_base_url.rstrip("/") or "http://127.0.0.1:8010"
    total = sum(float(item["line_total"]) for item in items)
    item_lines = "\n".join(f"- {item['part_name']} x {item['quantity']}" for item in items[:6])
    if len(items) > 6:
        item_lines += f"\n- +{len(items) - 6} kalem"
    message = (
        f"Yeni teklif talebi geldi.\n\n"
        f"Teklif No: #{quote_id}\n"
        f"Musteri: {(customer_name or 'Genel Musteri').strip() or 'Genel Musteri'}\n"
        f"Toplam: {total:.2f} TL\n\n"
        f"{item_lines}\n\n"
        f"Incele: {base_url}/admin/quotes"
    )

    for phone in phones:
        try:
            await whatsapp_client.send_text(phone, message)
            logger.info("Yeni teklif bildirimi gonderildi: %s", phone)
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:1000] if exc.response is not None else str(exc)
            logger.warning("Yeni teklif bildirimi gonderilemedi: %s -> %s", phone, detail)
        except (ValueError, httpx.HTTPError) as exc:
            logger.warning("Yeni teklif bildirimi gonderilemedi: %s -> %s", phone, exc)


def _notify_phones() -> list[str]:
    raw = settings.whatsapp_notify_phones or ""
    return [phone.strip().replace("+", "") for phone in raw.replace(";", ",").split(",") if phone.strip()]
