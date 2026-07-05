from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import json
from typing import Any


TWOPLACES = Decimal("0.01")
THREEPLACES = Decimal("0.001")
FOURPLACES = Decimal("0.0001")


def D(value: Any, default: str = "0") -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal(default)
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
        if value == "":
            return Decimal(default)
    return Decimal(str(value))


def q2(value: Any) -> Decimal:
    return D(value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def q3(value: Any) -> Decimal:
    return D(value).quantize(THREEPLACES, rounding=ROUND_HALF_UP)


def q4(value: Any) -> Decimal:
    return D(value).quantize(FOURPLACES, rounding=ROUND_HALF_UP)


def dumps_json(data: Any) -> str:
    def default(o):
        if isinstance(o, Decimal):
            return float(o)
        return str(o)

    return json.dumps(data, default=default, ensure_ascii=False)


def loads_json(data: str | bytes | None, fallback: Any) -> Any:
    if not data:
        return fallback
    return json.loads(data)
