from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.utils import D
from app.ventilation.formulas import calculate_geometry


NO_QUANTITY_PARTS: set[str] = set()


def sales_fields(part_code: str, inputs: dict, result: dict, calculation_quantity: object, line_total: object) -> dict:
    multiplier = D(calculation_quantity)
    if part_code == "spiro_boru":
        quantity = D(inputs.get("uzunluk") or 0) * multiplier
        unit = "m"
    elif part_code == "dikdortgen_kanal":
        geometry = result if result.get("alan_m2") is not None else calculate_geometry(part_code, inputs)
        quantity = D(geometry.get("alan_m2") or 0) * multiplier
        unit = "m2"
    else:
        quantity = multiplier
        unit = "adet"

    if quantity <= 0:
        raise ValueError("Teklif miktarı sıfırdan büyük olmalı.")
    unit_price = (D(line_total) / quantity).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    return {
        "sales_quantity": float(quantity),
        "sales_unit": unit,
        "sales_unit_label": "m²" if unit == "m2" else unit,
        "sales_unit_price": float(unit_price),
        "sales_quantity_text": format_quantity(quantity),
    }


def format_quantity(value: object) -> str:
    amount = D(value).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    text = format(amount, "f").rstrip("0").rstrip(".")
    return text.replace(".", ",") or "0"
