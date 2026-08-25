from __future__ import annotations

import re
from typing import Any

from app.ventilation.part_config import PARTS


def _val(inputs: dict[str, Any], key: str) -> str | None:
    value = inputs.get(key)
    if value in (None, ""):
        return None
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def _rect(inputs: dict[str, Any], w_key: str, h_key: str) -> str | None:
    w = _val(inputs, w_key)
    h = _val(inputs, h_key)
    return f"{w}x{h}cm" if w and h else None


def _cap(inputs: dict[str, Any], key: str = "cap") -> str | None:
    d = _val(inputs, key)
    return f"Ø{d}mm" if d else None


def part_measure_text(part_code: str, inputs: dict[str, Any]) -> str:
    if not isinstance(inputs, dict):
        return ""
    if part_code == "dikdortgen_kanal":
        return " ".join(x for x in [_rect(inputs, "agiz_en", "agiz_boy"), f"L:{_val(inputs, 'uzunluk')}m" if _val(inputs, "uzunluk") else None] if x)
    if part_code == "kare_dirsek":
        return " ".join(x for x in [_rect(inputs, "agiz_en", "agiz_boy"), f"{_val(inputs, 'aci')}°" if _val(inputs, "aci") else None] if x)
    if part_code in ("kare_es_1", "kare_es_2"):
        return " ".join(x for x in [_rect(inputs, "agiz_en", "agiz_boy"), f"H:{_val(inputs, 'yukseklik')}cm" if _val(inputs, "yukseklik") else None] if x)
    if part_code == "kare_reduksiyon":
        big = _rect(inputs, "ust_en", "ust_boy"); small = _rect(inputs, "alt_en", "alt_boy")
        return " ".join(x for x in [f"{big}->{small}" if big and small else None, f"H:{_val(inputs, 'yukseklik')}cm" if _val(inputs, "yukseklik") else None] if x)
    if part_code == "kare_saplama":
        return _rect(inputs, "agiz_en", "agiz_boy") or ""
    if part_code == "kutu":
        en = _val(inputs, "en")
        boy = _val(inputs, "boy")
        yukseklik = _val(inputs, "yukseklik")
        olcu = f"{en}x{boy}x{yukseklik}cm" if en and boy and yukseklik else None
        return " ".join(x for x in [olcu, _cap(inputs)] if x)
    if part_code == "spiro_boru":
        return " ".join(x for x in [_cap(inputs), f"L:{_val(inputs, 'uzunluk')}m" if _val(inputs, "uzunluk") else None] if x)
    if part_code == "yuvarlak_dirsek":
        return " ".join(x for x in [_cap(inputs), f"{_val(inputs, 'aci')}°" if _val(inputs, "aci") else None] if x)
    if "cap" in inputs:
        return " ".join(x for x in [_cap(inputs), f"L:{_val(inputs, 'uzunluk') or _val(inputs, 'boy')}cm" if (_val(inputs, "uzunluk") or _val(inputs, "boy")) else None] if x)
    cfg = PARTS.get(part_code, {})
    values = []
    for key, label in cfg.get("fields", []):
        value = _val(inputs, key)
        if value:
            values.append(f"{label.split('(')[0].strip()}:{value}")
    return " ".join(values)


def parasut_measure_text(part_code: str, inputs: dict[str, Any]) -> str:
    text = part_measure_text(part_code, inputs)
    if part_code == "spiro_boru":
        return re.sub(r"\s*L:[^\s]+m", "", text)
    return text


def part_description(part_code: str, part_name: str, inputs: dict[str, Any]) -> str:
    measure = part_measure_text(part_code, inputs)
    return f"{part_name} {measure}" if measure else part_name
