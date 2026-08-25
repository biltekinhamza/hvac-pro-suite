from __future__ import annotations

import secrets

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from app.accounting.parasut_service import parasut_service
from app.config import ASSET_VERSION, TEMPLATE_DIR, settings
from app.database import db
from app.models import AddMaterialOptionRequest, CalculateRequest, CartItemRequest, LaborRatesUpdateRequest, MaterialAvailabilityUpdateRequest, MaterialCostUpdateRequest, QuoteCreateRequest, QuoteMergeRequest
from app.quote_pdf import build_quote_pdf
from app.repository import repository
from app.utils import loads_json
from app.ventilation.engine import CostEngine
from app.ventilation.formulas import calculate_geometry
from app.ventilation.part_config import PARTS
from app.ventilation.part_description import part_measure_text, parasut_measure_text
from app.ventilation.sales_units import NO_QUANTITY_PARTS, sales_fields
from app.ventilation.service import ventilation_service


router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
templates.env.globals["asset_version"] = ASSET_VERSION
engine = CostEngine(repository)
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
    cart_token = request.cookies.get("order_cart_token")
    if not cart_token:
        cart_token = secrets.token_urlsafe(24)
    repository.get_active_cart(cart_token)
    response = templates.TemplateResponse("order.html", {"request": request})
    response.set_cookie("order_cart_token", cart_token, httponly=True, samesite="lax")
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/order", include_in_schema=False)
@router.get("/siparis", include_in_schema=False)
def order_page_compat_redirect(request: Request) -> RedirectResponse:
    query = request.url.query
    return RedirectResponse(url=f"/?{query}" if query else "/", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/admin/quotes", response_class=HTMLResponse)
def admin_quotes_page(request: Request, _admin: str = Depends(require_admin)):
    return templates.TemplateResponse("admin_quotes.html", {"request": request})


@router.get("/admin/carts", response_class=HTMLResponse)
def admin_carts_page(request: Request, _admin: str = Depends(require_admin)):
    return templates.TemplateResponse("admin_carts.html", {"request": request})


@router.get("/admin/materials", response_class=HTMLResponse)
def admin_materials_page(request: Request, _admin: str = Depends(require_admin)):
    return templates.TemplateResponse("admin_materials.html", {"request": request})


@router.get("/admin/legacy-carts/{cart_id}/open")
def open_legacy_cart(cart_id: int, _admin: str = Depends(require_admin)) -> RedirectResponse:
    cart_token = secrets.token_urlsafe(24)
    try:
        repository.claim_legacy_cart(cart_id, cart_token)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie("order_cart_token", cart_token, httponly=True, samesite="lax")
    return response


@router.get("/api/parts")
def get_parts(response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return {"items": ventilation_service.parts()}


@router.get("/api/admin/quotes")
def list_admin_quotes(_admin: str = Depends(require_admin)) -> dict:
    return {"items": [repository.serialize_quote(row) for row in repository.list_quotes()]}


@router.get("/api/admin/materials")
def list_admin_materials(_admin: str = Depends(require_admin)) -> dict:
    return {"items": [_serialize_material_option(row) for row in repository.list_material_options()]}


@router.get("/api/admin/carts")
def list_admin_carts(_admin: str = Depends(require_admin)) -> dict:
    carts = []
    for cart in repository.list_pending_carts():
        items = []
        for row in repository.list_cart_items_for_admin(int(cart["id"])):
            inputs = loads_json(row["inputs_json"], {})
            quantity = int(row["quantity"])
            result = calculate_geometry(row["part_code"], inputs)
            unit_data = sales_fields(row["part_code"], inputs, result, quantity, 0)
            measure = part_measure_text(row["part_code"], inputs)
            items.append({"id": row["id"], "part_code": row["part_code"], "part_name": PARTS[row["part_code"]]["title"], "measure": measure, "quantity": quantity, "inputs": inputs, **unit_data})
        carts.append({
            "id": cart["id"],
            "created_at": cart["created_at"],
            "customer_name": cart["customer_name"] or "",
            "whatsapp_phone": cart["whatsapp_phone"] or "",
            "item_count": int(cart["item_count"]),
            "items": items,
        })
    return {"items": carts}


@router.get("/api/admin/parasut/contacts")
async def search_admin_parasut_contacts(q: str = "", _admin: str = Depends(require_admin)) -> dict:
    try:
        items = await parasut_service.search_contacts(q, limit=20)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:1000] if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"Paraşüt API hatası: {detail}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Paraşüt bağlantı hatası: {exc}") from exc
    return {"items": items}


@router.put("/api/admin/carts/{cart_id}/items/{item_id}")
def update_admin_cart_item(cart_id: int, item_id: int, payload: CartItemRequest, _admin: str = Depends(require_admin)) -> dict:
    try:
        inputs = _normalize_inputs(payload.inputs, payload.profit_rate)
        _ensure_customer_material_stock(inputs)
        engine.calculate(payload.part_code, inputs)
        repository.update_cart_item_for_admin(cart_id, item_id, inputs, payload.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.delete("/api/admin/carts/{cart_id}/items/{item_id}")
def delete_admin_cart_item(cart_id: int, item_id: int, _admin: str = Depends(require_admin)) -> dict:
    try:
        repository.delete_cart_item_for_admin(cart_id, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@router.delete("/api/admin/carts/{cart_id}")
def delete_admin_cart(cart_id: int, _admin: str = Depends(require_admin)) -> dict:
    try:
        repository.cancel_pending_cart(cart_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/api/admin/carts/{cart_id}/quote")
async def create_admin_cart_quote(cart_id: int, payload: QuoteCreateRequest, _admin: str = Depends(require_admin)) -> dict:
    rows = repository.list_cart_items_for_admin(cart_id)
    if not rows:
        raise HTTPException(status_code=400, detail="Sepet boş.")
    prepared = _prepare_cart_quote_items(rows)
    try:
        quote_id = repository.create_quote_for_admin(cart_id, payload.customer_name, payload.shipping_amount, prepared)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "quote_id": quote_id}


@router.get("/api/admin/materials/names")
def list_material_names(_admin: str = Depends(require_admin)) -> dict:
    return {"items": [{"name": r["name"], "unit": r["unit"]} for r in repository.list_materials()]}


@router.get("/api/admin/labor-rates")
def get_labor_rates(_admin: str = Depends(require_admin)) -> dict:
    return repository.get_labor_rates()


@router.post("/api/admin/labor-rates")
def update_labor_rates(payload: LaborRatesUpdateRequest, _admin: str = Depends(require_admin)) -> dict:
    repository.update_labor_rates(payload.fitting, payload.square_duct, payload.spiro)
    return {"ok": True, **repository.get_labor_rates()}


@router.post("/api/admin/materials")
def add_admin_material(payload: AddMaterialOptionRequest, _admin: str = Depends(require_admin)) -> dict:
    row = repository.add_material_option(payload.material_name, payload.option_name, payload.average_unit_cost)
    return {"ok": True, "item": _serialize_material_option(row)}


@router.post("/api/admin/materials/{option_id}")
def update_admin_material(option_id: int, payload: MaterialCostUpdateRequest, _admin: str = Depends(require_admin)) -> dict:
    try:
        row = repository.update_material_option_cost(option_id, payload.average_unit_cost)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "item": _serialize_material_option(row)}


@router.post("/api/admin/materials/{option_id}/availability")
def update_admin_material_availability(option_id: int, payload: MaterialAvailabilityUpdateRequest, _admin: str = Depends(require_admin)) -> dict:
    try:
        row = repository.update_material_option_availability(option_id, payload.is_available)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "item": _serialize_material_option(row)}


@router.delete("/api/admin/materials/{option_id}")
def delete_admin_material(option_id: int, _admin: str = Depends(require_admin)) -> dict:
    try:
        repository.delete_material_option(option_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/api/admin/quotes/merge")
def merge_admin_quotes(payload: QuoteMergeRequest, _admin: str = Depends(require_admin)) -> dict:
    quote_ids = list(dict.fromkeys(payload.quote_ids))
    if len(quote_ids) < 2:
        raise HTTPException(status_code=400, detail="En az iki teklif seçin.")
    try:
        new_quote_id = _merge_quotes(quote_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "quote_id": new_quote_id, **_admin_quote_payload(new_quote_id)}


@router.post("/api/admin/quotes/delete")
async def delete_admin_quotes(request: Request, _admin: str = Depends(require_admin)) -> dict:
    payload = await request.json()
    quote_ids = list(dict.fromkeys(int(item) for item in payload.get("quote_ids", []) if item))
    if not quote_ids:
        raise HTTPException(status_code=400, detail="Silmek için teklif seçin.")
    try:
        deleted = repository.delete_quotes(quote_ids)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "deleted": deleted}


@router.get("/api/admin/quotes/{quote_id}")
def get_admin_quote(quote_id: int, _admin: str = Depends(require_admin)) -> dict:
    return _admin_quote_payload(quote_id)


@router.get("/api/admin/quotes/{quote_id}/pdf")
def get_admin_quote_pdf(quote_id: int, _admin: str = Depends(require_admin)) -> Response:
    pdf = build_quote_pdf(_admin_quote_payload(quote_id), settings)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="teklif-{quote_id}.pdf"'},
    )


@router.post("/api/admin/quotes/{quote_id}/items")
def add_admin_quote_item(quote_id: int, payload: CartItemRequest, _admin: str = Depends(require_admin)) -> dict:
    try:
        quote, _items = repository.get_quote(quote_id)
        item = _prepare_quote_item(quote, payload.part_code, payload.inputs, payload.quantity)
        repository.add_quote_item(quote_id, item)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, **_admin_quote_payload(quote_id)}


@router.put("/api/admin/quotes/{quote_id}/items/{item_id}")
def update_admin_quote_item(quote_id: int, item_id: int, payload: CartItemRequest, _admin: str = Depends(require_admin)) -> dict:
    try:
        quote, _items = repository.get_quote(quote_id)
        item = _prepare_quote_item(quote, payload.part_code, payload.inputs, payload.quantity)
        repository.update_quote_item(quote_id, item_id, item)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, **_admin_quote_payload(quote_id)}


@router.delete("/api/admin/quotes/{quote_id}/items/{item_id}")
def delete_admin_quote_item(quote_id: int, item_id: int, _admin: str = Depends(require_admin)) -> dict:
    try:
        repository.delete_quote_item(quote_id, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, **_admin_quote_payload(quote_id)}


@router.post("/api/admin/quotes/{quote_id}/profit")
async def apply_admin_quote_profit(quote_id: int, request: Request, _admin: str = Depends(require_admin)) -> dict:
    payload = await request.json()
    try:
        profit_rate = payload.get("profit_rate", 0)
        quote, items = repository.get_quote(quote_id)
        quote_data = repository.serialize_quote(quote)
        quote_data["profit_rate"] = profit_rate
        repriced_items = []
        for row in items:
            saved = repository.serialize_quote_item(row)
            repriced = _prepare_quote_item(
                quote_data,
                saved["part_code"],
                saved["inputs"],
                saved["quantity"],
            )
            repriced_items.append({"id": saved["id"], **repriced})
        repository.apply_quote_profit_rate(quote_id, profit_rate, repriced_items)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, **_admin_quote_payload(quote_id)}


@router.post("/api/admin/quotes/{quote_id}/shipping")
async def apply_admin_quote_shipping(quote_id: int, request: Request, _admin: str = Depends(require_admin)) -> dict:
    payload = await request.json()
    try:
        repository.apply_quote_shipping_amount(quote_id, payload.get("shipping_amount", 0))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, **_admin_quote_payload(quote_id)}


@router.post("/api/admin/quotes/{quote_id}/send-to-parasut")
async def send_admin_quote_to_parasut(quote_id: int, _admin: str = Depends(require_admin)) -> dict:
    try:
        quote_row, item_rows = repository.get_quote(quote_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    quote = repository.serialize_quote(quote_row)
    if quote.get("parasut_offer_id"):
        repository.reset_quote_parasut(quote_id)
        quote["parasut_offer_id"] = None
        quote["status"] = "review"

    items = _decorate_quote_items([repository.serialize_quote_item(row) for row in item_rows], quote["profit_rate"])
    if not items:
        raise HTTPException(status_code=400, detail="Teklif kalemi yok.")

    try:
        parasut_offer_id = await parasut_service.create_offer_from_quote(quote, items)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Paraşüt ürün kodu bulunamadı: {exc}") from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:1000] if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"Paraşüt API hatası: {detail}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Paraşüt bağlantı hatası: {exc}") from exc

    repository.mark_quote_sent_to_parasut(quote_id, parasut_offer_id)
    return {"ok": True, "parasut_offer_id": parasut_offer_id, "already_sent": False}


@router.get("/api/material-options/{material_name}")
def get_material_options(material_name: str) -> dict:
    items = repository.find_available_options_by_name(material_name.upper())
    return {"items": [{"id": r["id"], "option_name": r["option_name"], "average_unit_cost": float(r["average_unit_cost"])} for r in items]}


@router.post("/api/calculate")
def calculate(payload: CalculateRequest) -> dict:
    inputs = _normalize_inputs(payload.inputs, payload.profit_rate)
    try:
        result = engine.calculate(payload.part_code, inputs)
        sale = engine.calculate_sale(result, payload.profit_rate, payload.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"result": result, "sale": sale}


@router.put("/api/cart/items/{item_id}")
def update_cart_item(item_id: int, payload: CartItemRequest, request: Request) -> dict:
    cart_token = _cart_token(request)
    try:
        if payload.part_code in NO_QUANTITY_PARTS:
            raise ValueError("Bu parçanın miktarı ölçülerinden hesaplanır.")
        repository.update_cart_item_quantity(cart_token, item_id, payload.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "cart": _cart_payload(cart_token)}

@router.delete("/api/cart/items/{item_id}")
def delete_cart_item(item_id: int, request: Request) -> dict:
    cart_token = _cart_token(request)
    try:
        repository.delete_cart_item(cart_token, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "cart": _cart_payload(cart_token)}

@router.post("/api/cart/items")
def add_cart_item(payload: CartItemRequest, request: Request) -> dict:
    cart_token = _cart_token(request)
    inputs = _normalize_inputs(payload.inputs, payload.profit_rate)
    try:
        _ensure_customer_material_stock(inputs)
        result = engine.calculate(payload.part_code, inputs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    quantity = 1 if payload.part_code in NO_QUANTITY_PARTS else payload.quantity
    sale = engine.calculate_sale(result, payload.profit_rate, quantity)
    item_id = repository.add_cart_item(cart_token, payload.part_code, inputs, quantity)
    return {"ok": True, "id": item_id, "result": result, "sale": sale, "cart": _cart_payload(cart_token)}


@router.get("/api/cart")
def get_cart(request: Request) -> dict:
    return _cart_payload(_cart_token(request))


def _prepare_cart_quote_items(rows) -> list[dict]:
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
    return prepared


@router.post("/api/quotes")
async def create_quote(payload: QuoteCreateRequest, request: Request) -> dict:
    cart_token = _cart_token(request)
    rows = repository.list_cart_items(cart_token)
    if not rows:
        raise HTTPException(status_code=400, detail="Sepet boş.")

    prepared = _prepare_cart_quote_items(rows)
    quote_id = repository.create_quote(cart_token, payload.customer_name, payload.shipping_amount, prepared)
    return {"ok": True, "quote_id": quote_id}


def _admin_quote_payload(quote_id: int) -> dict:
    try:
        quote, items = repository.get_quote(quote_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    serialized = _decorate_quote_items([repository.serialize_quote_item(row) for row in items], quote["profit_rate"])
    quote_data = repository.serialize_quote(quote)
    quote_data["total_amount"] = round(
        sum(float(item["line_total"]) for item in serialized) + float(quote_data["shipping_amount"]),
        2,
    )
    return {
        "quote": quote_data,
        "items": serialized,
        "summary": _quote_summary(serialized),
    }


def _prepare_quote_item(quote, part_code: str, inputs: dict[str, object], quantity: int) -> dict:
    if part_code not in PARTS:
        raise ValueError("Parça tipi bulunamadı.")
    profit_rate = float(quote["profit_rate"] or 0)
    data = _normalize_inputs(inputs, profit_rate)
    result = engine.calculate(part_code, data)
    sale = engine.calculate_sale(result, profit_rate, quantity)
    return {
        "part_code": part_code,
        "part_name": PARTS[part_code]["title"],
        "quantity": quantity,
        "unit_cost": sale["unit_cost"],
        "unit_price": sale["unit_price"],
        "line_total": sale["line_total"],
        "cut_area_m2": result["kesilen_m2"],
        "weight_kg": result["kg"],
        "inputs": data,
        "result": result,
    }


def _merge_quotes(quote_ids: list[int]) -> int:
    quotes = []
    groups: dict[tuple, dict] = {}
    for quote_id in quote_ids:
        quote, items = repository.get_quote(quote_id)
        quotes.append(quote)
        for row in items:
            item = repository.serialize_quote_item(row)
            key = _quote_item_merge_key(item["part_code"], item["inputs"])
            if key not in groups:
                groups[key] = {
                    "part_code": item["part_code"],
                    "inputs": item["inputs"],
                    "quantity": 0,
                }
            groups[key]["quantity"] += int(item["quantity"] or 0)

    if not groups:
        raise ValueError("Birleştirilecek teklif kalemi yok.")

    first_quote = quotes[0]
    prepared = [
        _prepare_quote_item(first_quote, group["part_code"], group["inputs"], group["quantity"])
        for group in groups.values()
    ]
    customer_name = "Birleşik Teklif (" + ", ".join(f"#{quote_id}" for quote_id in quote_ids) + ")"
    shipping_total = sum(float(quote["shipping_amount"] or 0) for quote in quotes)
    new_quote_id = repository.create_quote_from_items(customer_name, first_quote["profit_rate"] or 0, shipping_total, prepared)
    repository.mark_quotes_merged(quote_ids)
    return new_quote_id


def _quote_item_merge_key(part_code: str, inputs: dict) -> tuple:
    fields = []
    for key, _label in PARTS.get(part_code, {}).get("fields", []):
        fields.append((key, _normalize_merge_value(inputs.get(key))))
    fields.extend([
        ("sac_kalinlik_mm", _normalize_merge_value(inputs.get("sac_kalinlik_mm"))),
        ("sac_ozellik_id", _normalize_merge_value(inputs.get("sac_ozellik_id"))),
        ("izolasyon_ozellik_id", _normalize_merge_value(inputs.get("izolasyon_ozellik_id"))),
        ("boya_ekle", "1" if _is_checked(inputs.get("boya_ekle")) else "0"),
    ])
    return (part_code, tuple(fields))


def _normalize_merge_value(value: object) -> str:
    text = str(value or "").strip().replace(",", ".")
    if text.endswith(".0"):
        text = text[:-2]
    return text


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
    data.setdefault("boya_ozellik_id", "")
    data["profit_rate"] = str(profit_rate)
    return data


def _decorate_quote_items(items: list[dict], profit_rate: object = 0) -> list[dict]:
    for item in items:
        inputs = item.get("inputs") or {}
        measure = part_measure_text(item["part_code"], inputs)
        title_options = _quote_item_title_options(inputs)
        options = _quote_item_options(inputs)
        sac = str(inputs.get("sac_kalinlik_mm") or "").strip()

        result = engine.calculate(item["part_code"], inputs)
        sale = engine.calculate_sale(result, profit_rate, item["quantity"])
        item["result"] = result
        item["line_total"] = sale["line_total"]
        item["unit_cost"] = sale["unit_cost"]
        item["unit_price"] = sale["unit_price"]
        item["cut_area_m2"] = result["kesilen_m2"]
        item["weight_kg"] = result["kg"]

        display_name = item["part_name"] + (f" ({')-('.join(title_options)})" if title_options else "")
        unit_data = sales_fields(item["part_code"], inputs, result, item["quantity"], sale["line_total"])
        item.update(unit_data)
        detail_parts = [f"{unit_data['sales_quantity_text']} {unit_data['sales_unit_label']}"]
        if sac:
            detail_parts.append(f"Sac: {sac} mm")
        if measure:
            detail_parts.append(f"Ölçüler: {measure}")

        item["display"] = measure
        item["display_name"] = display_name
        item["options"] = options
        item["title_options"] = title_options
        item["detail_parts"] = detail_parts
        item["detail_text"] = " | ".join([display_name, *detail_parts])
        parasut_parts = list(detail_parts)
        parasut_measure = parasut_measure_text(item["part_code"], inputs)
        if parasut_measure != measure:
            parasut_parts = [part for part in parasut_parts if part != f"Ölçüler: {measure}"]
            if parasut_measure:
                parasut_parts.append(f"Ölçüler: {parasut_measure}")
        item["parasut_description"] = f"{display_name} | {' | '.join(parasut_parts)}"
    return items


def _quote_item_title_options(inputs: dict) -> list[str]:
    opts = []
    if izo_id := inputs.get("izolasyon_ozellik_id"):
        try:
            opt = repository.get_material_option(int(izo_id))
            opts.append(str(opt["option_name"]))
        except (ValueError, TypeError):
            opts.append("İzolasyon")
    if _is_checked(inputs.get("boya_ekle")):
        opts.append("Boyalı")
    return opts


def _quote_item_options(inputs: dict) -> list[str]:
    opts = []
    if izo_id := inputs.get("izolasyon_ozellik_id"):
        try:
            opt = repository.get_material_option(int(izo_id))
            opts.append(f"İzolasyon: {opt['option_name']}")
        except (ValueError, TypeError):
            opts.append("İzolasyon")
    if _is_checked(inputs.get("boya_ekle")):
        opts.append("Boya")
    if _is_checked(inputs.get("flans_ekle")):
        opts.append("Flanş")
    if _is_checked(inputs.get("conta_ekle")):
        opts.append("Conta")
    if _is_checked(inputs.get("vida_ekle")):
        opts.append("Vida")
    return opts


def _quote_summary(items: list[dict]) -> dict:
    total_cut_m2 = sum(float(item["cut_area_m2"]) * item["quantity"] for item in items)
    total_kg = sum(float(item["weight_kg"]) * item["quantity"] for item in items)
    return {"total_cut_m2": round(total_cut_m2, 3), "total_kg": round(total_kg, 2)}


def _format_money_tr(value: object) -> str:
    return f"{float(value or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _is_checked(value: object) -> bool:
    return value is True or str(value).strip().lower() in {"1", "true", "on", "yes"}


def _ensure_customer_material_stock(inputs: dict[str, object]) -> None:
    try:
        thickness = float(str(inputs.get("sac_kalinlik_mm") or "").replace(",", "."))
    except ValueError as exc:
        raise ValueError("Geçerli bir sac kalınlığı seçin.") from exc
    available_sheets = repository.find_available_options_by_name("SAC")
    if not any(float(str(row["option_name"]).split()[0].replace(",", ".")) == thickness for row in available_sheets):
        raise ValueError("Seçilen sac stokta yok.")
    if isolation_id := inputs.get("izolasyon_ozellik_id"):
        available_ids = {int(row["id"]) for row in repository.find_available_options_by_name("IZOLASYON")}
        if int(isolation_id) not in available_ids:
            raise ValueError("Seçilen izolasyon stokta yok.")


def _cart_token(request: Request) -> str:
    token = request.cookies.get("order_cart_token")
    if not token:
        raise HTTPException(status_code=400, detail="Sipariş oturumu bulunamadı. Sayfayı yenileyin.")
    return token


def _cart_payload(cart_token: str) -> dict:
    rows = repository.list_cart_items(cart_token)
    items = []
    total = 0.0
    for row in rows:
        inputs = loads_json(row["inputs_json"], {})
        result = engine.calculate(row["part_code"], inputs)
        sale = engine.calculate_sale(result, inputs.get("profit_rate", "0"), row["quantity"])
        line_total = float(sale["line_total"])
        total += line_total
        title_options = _quote_item_title_options(inputs)
        cart_options = [option for option in _quote_item_options(inputs) if option.startswith(("İzolasyon", "Boya"))]
        display_name = PARTS[row["part_code"]]["title"] + (f" ({')-('.join(title_options)})" if title_options else "")
        items.append({
            "id": row["id"],
            "part_code": row["part_code"],
            "part_name": PARTS[row["part_code"]]["title"],
            "display_name": display_name,
            "quantity": row["quantity"],
            "inputs": inputs,
            "display": part_measure_text(row["part_code"], inputs),
            "options": cart_options,
            "result": result,
            "sale": sale,
            "line_total": line_total,
            **sales_fields(row["part_code"], inputs, result, row["quantity"], line_total),
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
        "is_available": bool(row["is_available"]),
    }
