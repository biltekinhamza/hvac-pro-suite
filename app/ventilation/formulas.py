from __future__ import annotations

import math
from typing import Callable

YOGUNLUK = 7850.0
KENET_GENISLIK_M = 0.02


def _f(data: dict[str, object], key: str) -> float:
    value = data.get(key, "")
    if value in (None, ""):
        raise ValueError(f"{key} boş olamaz")
    return float(str(value).replace(",", "."))


def cm_to_m(x: float) -> float:
    return x / 100.0


def mm_to_m(x: float) -> float:
    return x / 1000.0


def _kg(area_m2: float, thickness_mm: float) -> float:
    return area_m2 * mm_to_m(thickness_mm) * YOGUNLUK


def _sonuc(alan_m2: float, thickness_mm: float, fire_orani: float = 1.0, detay: dict | None = None) -> dict:
    kesilen_m2 = alan_m2 * fire_orani
    return {"alan_m2": round(alan_m2, 3), "kesilen_m2": round(kesilen_m2, 3), "kg": round(_kg(kesilen_m2, thickness_mm), 2), "detay": detay or {}}


def hesap_dikdortgen_kanal(post: dict[str, object]) -> dict:
    w = cm_to_m(_f(post, "agiz_en"))
    h = cm_to_m(_f(post, "agiz_boy"))
    l = _f(post, "uzunluk")
    t = _f(post, "sac_kalinlik_mm")
    alan_m2 = 2 * (w + h) * l
    kenet_m2 = l * KENET_GENISLIK_M
    kesilen_m2 = (alan_m2 + kenet_m2) * 1.05
    return {"alan_m2": round(alan_m2, 3), "kesilen_m2": round(kesilen_m2, 3), "kg": round(_kg(kesilen_m2, t), 2), "detay": {"acilim_m2": round(alan_m2, 3), "kenet_m2": round(kenet_m2, 3)}}


def hesap_kare_dirsek(post):
    w = cm_to_m(_f(post, "agiz_en")); h = cm_to_m(_f(post, "agiz_boy")); aci = _f(post, "aci"); t = _f(post, "sac_kalinlik_mm")
    R = min(w, h); yay_boyu = (math.pi * R * aci) / 180; cevre = 2 * (w + h); alan_m2 = cevre * yay_boyu
    return {"alan_m2": round(alan_m2, 3), "kesilen_m2": round(alan_m2 * 1.10, 3), "kg": round(_kg(alan_m2 * 1.10, t), 2), "detay": {"yaricap_m": round(R, 3), "yay_boyu_m": round(yay_boyu, 3)}}


def hesap_kare_es_1(post):
    return _sonuc(2 * (cm_to_m(_f(post, "agiz_en")) + cm_to_m(_f(post, "agiz_boy"))) * cm_to_m(_f(post, "yukseklik")), _f(post, "sac_kalinlik_mm"), 1.05)


def hesap_kare_es_2(post):
    return hesap_kare_es_1(post)


def hesap_kare_pantolon(post):
    g_en = cm_to_m(_f(post, "giris_en")); g_boy = cm_to_m(_f(post, "giris_boy")); c_en = cm_to_m(_f(post, "cikis_en")); c_boy = cm_to_m(_f(post, "cikis_boy")); y = cm_to_m(_f(post, "yukseklik")); t = _f(post, "sac_kalinlik_mm")
    alan_m2 = (g_en + g_boy + 2 * (c_en + c_boy)) * y
    return _sonuc(alan_m2, t, 1.10)


def hesap_kare_pantolon_2(post):
    y = cm_to_m(_f(post, "yukseklik")); toplam = sum([cm_to_m(_f(post, "giris_en")), cm_to_m(_f(post, "giris_boy")), cm_to_m(_f(post, "cikis1_en")), cm_to_m(_f(post, "cikis1_boy")), cm_to_m(_f(post, "cikis2_en")), cm_to_m(_f(post, "cikis2_boy"))])
    return _sonuc(toplam * y, _f(post, "sac_kalinlik_mm"), 1.10)


def hesap_kare_istavroz(post):
    y = cm_to_m(_f(post, "yukseklik")); toplam = sum(cm_to_m(_f(post, key)) for key in ["ana_giris_en", "ana_giris_boy", "ana_cikis_en", "ana_cikis_boy", "sol_kol_en", "sol_kol_boy", "sag_kol_en", "sag_kol_boy"])
    return _sonuc(toplam * y, _f(post, "sac_kalinlik_mm"), 1.15)


def hesap_kare_reduksiyon(post):
    ust_cevre = cm_to_m(2 * (_f(post, "ust_en") + _f(post, "ust_boy"))); alt_cevre = cm_to_m(2 * (_f(post, "alt_en") + _f(post, "alt_boy"))); y = cm_to_m(_f(post, "yukseklik")); t = _f(post, "sac_kalinlik_mm")
    return _sonuc(((ust_cevre + alt_cevre) / 2) * y, t, 1.05)


def hesap_kutu(post):
    en = cm_to_m(_f(post, "en")); boy = cm_to_m(_f(post, "boy")); y = cm_to_m(_f(post, "yukseklik")); cap = mm_to_m(_f(post, "cap")); t = _f(post, "sac_kalinlik_mm")
    return _sonuc(2 * (en * boy + en * y + boy * y) - math.pi * (cap / 2) ** 2, t)


def hesap_kare_kapak(post):
    return _sonuc(cm_to_m(_f(post, "en")) * cm_to_m(_f(post, "boy")), _f(post, "sac_kalinlik_mm"), 1.02)


def hesap_kareden_yuvarlaga(post):
    kare_cevre = 2 * (cm_to_m(_f(post, "kare_en")) + cm_to_m(_f(post, "kare_boy"))); cap = mm_to_m(_f(post, "yuvarlak_cap")); y = cm_to_m(_f(post, "yukseklik")); yuvarlak_cevre = math.pi * cap
    return _sonuc(((kare_cevre + yuvarlak_cevre) / 2) * y, _f(post, "sac_kalinlik_mm"), 1.10)


def hesap_kortapa(post):
    cap = mm_to_m(_f(post, "cap")); girme = cm_to_m(_f(post, "girme_payi"))
    return _sonuc(math.pi * (cap / 2) ** 2 + math.pi * cap * girme, _f(post, "sac_kalinlik_mm"), 1.05)


def hesap_yuvarlak_istavroz(post):
    ana = mm_to_m(_f(post, "ana_cap")); kol = mm_to_m(_f(post, "kol_cap")); l1 = cm_to_m(_f(post, "ana_boy")); l2 = cm_to_m(_f(post, "kol_boy"))
    return _sonuc(math.pi * ana * l1 + 2 * math.pi * kol * l2, _f(post, "sac_kalinlik_mm"), 1.10)


def hesap_yuvarlak_mason(post):
    return _sonuc(math.pi * mm_to_m(_f(post, "cap")) * cm_to_m(_f(post, "boy")), _f(post, "sac_kalinlik_mm"), 1.02)


def hesap_spiro_boru(post: dict[str, object]) -> dict:
    d = mm_to_m(_f(post, "cap")); l = cm_to_m(_f(post, "uzunluk")); t = _f(post, "sac_kalinlik_mm"); alan_m2 = math.pi * d * l
    return _sonuc(alan_m2, t, 1.05, {"acilim_m2": round(alan_m2, 3)})


def hesap_yuvarlak_dirsek(post: dict[str, object]) -> dict:
    d = mm_to_m(_f(post, "cap")); aci = _f(post, "aci"); r = cm_to_m(_f(post, "r")); t = _f(post, "sac_kalinlik_mm"); theta = math.pi * aci / 180.0; cevre = math.pi * d; yay = r * theta; alan_m2 = cevre * yay; kesilen_m2 = (alan_m2 + (4 - 1) * cevre * 0.02 + yay * 0.02) * 1.05
    return {"alan_m2": round(alan_m2, 3), "kesilen_m2": round(kesilen_m2, 3), "kg": round(_kg(kesilen_m2, t), 2), "detay": {"acilim_m2": round(alan_m2, 3)}}


def hesap_yuvarlak_reduksiyon(post: dict[str, object]) -> dict:
    d1 = mm_to_m(_f(post, "buyuk_cap")); d2 = mm_to_m(_f(post, "kucuk_cap")); h = cm_to_m(_f(post, "boy")); t = _f(post, "sac_kalinlik_mm"); l = math.sqrt(h ** 2 + ((d1 - d2) / 2) ** 2)
    return _sonuc(math.pi * ((d1 + d2) / 2) * l, t, 1.05)


def hesap_yuvarlak_te(post: dict[str, object]) -> dict:
    alan_m2 = (math.pi * mm_to_m(_f(post, "ana_cap")) * cm_to_m(_f(post, "ana_boy"))) + (math.pi * mm_to_m(_f(post, "kol_cap")) * cm_to_m(_f(post, "kol_boy")))
    return _sonuc(alan_m2, _f(post, "sac_kalinlik_mm"), 1.05)


HESAPLAYICILAR: dict[str, Callable[[dict[str, object]], dict]] = {name.replace("hesap_", ""): func for name, func in list(globals().items()) if name.startswith("hesap_") and callable(func)}


def calculate_geometry(part_code: str, data: dict[str, object]) -> dict:
    try:
        fn = HESAPLAYICILAR[part_code]
    except KeyError as exc:
        raise ValueError(f"Parça hesaplayıcısı bulunamadı: {part_code}") from exc
    return fn(data)
