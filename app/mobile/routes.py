from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.mobile.models import ActivationRequest, OperationRequest
from app.mobile.repository import mobile_repository
from app.repository import repository
from app.ventilation.engine import CostEngine
from app.ventilation.part_config import PARTS
from app.ventilation.service import ventilation_service


router = APIRouter(prefix="/api/v1", tags=["mobile"])
bearer = HTTPBearer(auto_error=False)
engine = CostEngine(repository)


def _require_https(request: Request) -> None:
    if settings.app_env.lower() not in {"development", "test"} and request.url.scheme != "https":
        raise HTTPException(status_code=400, detail="HTTPS gerekli.")


def require_device(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
):
    _require_https(request)
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token gerekli.")
    device = mobile_repository.device_for_token(credentials.credentials)
    if not device:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token gecersiz.")
    return device


@router.post("/activate")
def activate(payload: ActivationRequest, request: Request) -> dict:
    _require_https(request)
    if not settings.mobile_activation_code:
        raise HTTPException(status_code=503, detail="Mobil aktivasyon yapilandirilmamis.")
    if not secrets.compare_digest(payload.activation_code, settings.mobile_activation_code):
        raise HTTPException(status_code=403, detail="Aktivasyon kodu gecersiz.")
    token = mobile_repository.activate(settings.mobile_tenant_id, payload.device_id, payload.device_name)
    return {"token": token, "token_type": "bearer", "tenant_id": settings.mobile_tenant_id, "company_name": settings.company_name}


@router.get("/catalog")
def catalog(_device=Depends(require_device)) -> dict:
    materials = [
        {"id": row["id"], "name": row["name"], "option_name": row["option_name"], "unit": row["unit"]}
        for row in repository.list_material_options()
        if row["is_available"]
    ]
    return {"parts": ventilation_service.parts(), "material_options": materials}


@router.post("/operations")
def operation(payload: OperationRequest, device=Depends(require_device)) -> dict:
    draft = payload.draft.model_dump()
    draft["device_db_id"] = device["id"]
    prepared = []
    try:
        for item in draft["items"]:
            if item["part_code"] not in PARTS:
                raise ValueError("Parca tipi bulunamadi.")
            inputs = _normalize_inputs(item["inputs"], draft["profit_rate"])
            item["inputs"] = inputs
            result = engine.calculate(item["part_code"], inputs)
            sale = engine.calculate_sale(result, draft["profit_rate"], item["quantity"])
            prepared.append({
                "part_code": item["part_code"], "part_name": PARTS[item["part_code"]]["title"],
                "quantity": item["quantity"], "inputs": inputs, "result": result,
                "unit_cost": sale["unit_cost"], "unit_price": sale["unit_price"], "line_total": sale["line_total"],
                "cut_area_m2": result["kesilen_m2"], "weight_kg": result["kg"],
            })
        return mobile_repository.run_operation(device, payload.operation_id, payload.type, draft, prepared)
    except ValueError as exc:
        code = 409 if "operation_id" in str(exc) else 400
        raise HTTPException(status_code=code, detail=str(exc)) from exc


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
