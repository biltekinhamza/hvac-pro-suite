from __future__ import annotations

import math
from typing import Callable

from app.ventilation.agiz import agizlari_getir

YOGUNLUK = 7850.0
KENET_GENISLIK_M = 0.02
FLANS_PAYI_CM = 3.0

# JKF galvanizli jetkap kataloğundaki flanşlı ürünler:
# çap (mm): (referans sac kalınlığı (mm), bitmiş ürün ağırlığı (kg))
JETKAP_KATALOG_AGIRLIKLARI = {
    120: (0.90, 2.20),
    125: (0.90, 2.25),
    140: (0.90, 2.75),
    150: (0.90, 3.25),
    160: (0.90, 3.65),
    180: (0.90, 4.35),
    200: (0.90, 5.10),
    225: (0.90, 6.10),
    250: (0.90, 8.15),
    275: (0.90, 8.50),
    300: (0.90, 10.35),
    315: (0.90, 11.10),
    350: (0.90, 13.20),
    400: (0.90, 17.20),
    450: (0.90, 21.00),
    500: (0.90, 28.30),
    550: (0.90, 33.60),
    600: (0.90, 37.20),
    630: (0.90, 39.70),
    650: (0.90, 42.30),
    700: (1.25, 64.40),
    750: (1.25, 71.50),
    800: (1.25, 80.70),
    850: (1.25, 91.70),
    900: (1.25, 102.60),
    950: (1.25, 112.00),
    1000: (1.25, 120.00),
    1100: (1.25, 147.70),
    1250: (1.25, 161.00),
}

# ABG galvanizli konik yağmur şapkası kataloğu:
# çap (mm): (referans sac kalınlığı (mm), bitmiş ürün ağırlığı (kg))
SAPKA_KATALOG_AGIRLIKLARI = {
    80: (0.90, 1.30),
    100: (0.90, 1.35),
    120: (0.90, 1.40),
    125: (0.90, 1.50),
    140: (0.90, 1.90),
    150: (0.90, 2.20),
    160: (0.90, 2.40),
    180: (0.90, 2.66),
    200: (0.90, 4.00),
    225: (0.90, 5.30),
    250: (0.90, 5.90),
    275: (0.90, 6.00),
    300: (0.90, 6.10),
    315: (0.90, 6.12),
    350: (0.90, 6.14),
    400: (0.90, 6.30),
    450: (0.90, 7.00),
    500: (0.90, 9.70),
    550: (0.90, 9.70),
    600: (0.90, 12.00),
    630: (0.90, 10.40),
    650: (0.90, 11.00),
    700: (0.90, 19.20),
    750: (0.90, 20.90),
    800: (1.25, 22.30),
    850: (1.25, 26.90),
    900: (1.25, 29.70),
    950: (1.25, 31.35),
    1000: (1.25, 34.50),
    1100: (1.25, 38.00),
    1250: (1.25, 43.20),
}


def _f(data: dict[str, object], key: str) -> float:
    value = data.get(key, "")
    if value in (None, ""):
        raise ValueError(f"{key} boş olamaz")
    return float(str(value).replace(",", "."))


def cm_to_m(x: float) -> float:
    return x / 100.0


def poligon_alani_cm2(noktalar: list[tuple[float, float]]) -> float:
    toplam = 0.0
    n = len(noktalar)
    for i in range(n):
        x1, y1 = noktalar[i]
        x2, y2 = noktalar[(i + 1) % n]
        toplam += x1 * y2 - y1 * x2
    return abs(toplam) / 2.0


def mm_to_m(x: float) -> float:
    return x / 1000.0


def kenar_uzunlugu_cm(noktalar: list[tuple[float, float]], kenar_indisleri: list[tuple[int, int]]) -> float:
    toplam = 0.0
    for i, j in kenar_indisleri:
        x1, y1 = noktalar[i]
        x2, y2 = noktalar[j]
        toplam += math.hypot(x2 - x1, y2 - y1)
    return toplam


def hesap_genel_offset(
    yanak_vertices: list[tuple[float, float]],
    sargi_kenarlari: list[tuple[int, int]],
    kanal_genisligi_cm: float,
    fire_orani: float = 0.15,
    flans_alani_cm2: float = 0,
    kenet_alani_cm2: float = 0,
    ek_alani_cm2: float = 0,
    sac_kalinligi_mm: float = 0.80,
) -> dict:
    yanak_alani_cm2 = poligon_alani_cm2(yanak_vertices)
    sargi_boyu_cm = kenar_uzunlugu_cm(yanak_vertices, sargi_kenarlari)
    sargi_alani_cm2 = sargi_boyu_cm * kanal_genisligi_cm
    net_alan_cm2 = 2 * yanak_alani_cm2 + sargi_alani_cm2 + flans_alani_cm2 + kenet_alani_cm2 + ek_alani_cm2
    fireli_alan_cm2 = net_alan_cm2 / (1 - fire_orani)
    fire_alani_cm2 = fireli_alan_cm2 - net_alan_cm2
    alan_m2 = net_alan_cm2 / 10000.0
    kesilen_m2 = fireli_alan_cm2 / 10000.0
    return {
        "alan_m2": round(alan_m2, 3),
        "kesilen_m2": round(kesilen_m2, 3),
        "kg": round(_kg(kesilen_m2, sac_kalinligi_mm), 2),
        "detay": {
            "yanak_alani_cm2": round(yanak_alani_cm2, 2),
            "sargi_alani_cm2": round(sargi_alani_cm2, 2),
            "flans_alani_cm2": round(flans_alani_cm2, 2),
            "kenet_alani_cm2": round(kenet_alani_cm2, 2),
            "ek_alani_cm2": round(ek_alani_cm2, 2),
            "fire_alani_cm2": round(fire_alani_cm2, 2),
        },
    }


def _kg(area_m2: float, thickness_mm: float) -> float:
    return area_m2 * mm_to_m(thickness_mm) * YOGUNLUK


def _sonuc(alan_m2: float, thickness_mm: float, fire_orani: float = 0.0, detay: dict | None = None) -> dict:
    kesilen_m2 = alan_m2 / (1 - fire_orani) if fire_orani > 0 else alan_m2
    return {"alan_m2": round(alan_m2, 3), "kesilen_m2": round(kesilen_m2, 3), "kg": round(_kg(kesilen_m2, thickness_mm), 2), "detay": detay or {}}


def _flans_alani_m2(post, part_code):
    agizlar = agizlari_getir(part_code, post)
    toplam = 0.0
    for a in agizlar:
        if a[0] == "dikdortgen":
            cevre_cm = 2 * (float(a[1]) + float(a[2]))
            toplam += (cevre_cm * FLANS_PAYI_CM) / 10000.0
    return toplam


def hesap_dikdortgen_kanal(post: dict[str, object]) -> dict:
    w = cm_to_m(_f(post, "agiz_en"))
    h = cm_to_m(_f(post, "agiz_boy"))
    l = _f(post, "uzunluk")
    t = _f(post, "sac_kalinlik_mm")
    alan_m2 = 2 * (w + h) * l
    kenet_m2 = l * KENET_GENISLIK_M
    parca_adedi = math.ceil(l / 1.2)
    flans_m2 = _flans_alani_m2(post, "dikdortgen_kanal") * parca_adedi
    kesilen_m2 = (alan_m2 + kenet_m2 + flans_m2) / 0.95
    return {"alan_m2": round(alan_m2, 3), "kesilen_m2": round(kesilen_m2, 3), "kg": round(_kg(kesilen_m2, t), 2), "detay": {"acilim_m2": round(alan_m2, 3), "kenet_m2": round(kenet_m2, 3), "flans_m2": round(flans_m2, 3), "parca_adedi": parca_adedi}}


def hesap_kare_dirsek(post):
    w = cm_to_m(_f(post, "agiz_en")); h = cm_to_m(_f(post, "agiz_boy")); aci = _f(post, "aci"); t = _f(post, "sac_kalinlik_mm")
    R = min(w, h); yay_boyu = (math.pi * R * aci) / 180; cevre = 2 * (w + h); alan_m2 = cevre * yay_boyu
    flans_m2 = _flans_alani_m2(post, "kare_dirsek")
    return _sonuc(alan_m2 + flans_m2, t, 0.10, {"yaricap_m": round(R, 3), "yay_boyu_m": round(yay_boyu, 3)})


def _f_opt(data: dict, key: str, default: float = 0.0) -> float:
    value = data.get(key, "")
    if value in (None, ""):
        return default
    return float(str(value).replace(",", "."))


def smoothstep(u: float) -> float:
    return 3.0 * u * u - 2.0 * u * u * u


def kare_es_1_vertices(H: float, L: float, K: float, n: int = 8) -> list[tuple[float, float]]:
    left_curve: list[tuple[float, float]] = []
    right_curve: list[tuple[float, float]] = []
    for i in range(n + 1):
        u = i / n
        y = L * u
        x_shift = K * smoothstep(u)
        left_curve.append((x_shift, y))
        right_curve.append((H + x_shift, y))
    vertices: list[tuple[float, float]] = []
    vertices.append(left_curve[0])
    vertices.append(right_curve[0])
    for p in right_curve[1:]:
        vertices.append(p)
    vertices.append(left_curve[-1])
    for p in reversed(left_curve[1:-1]):
        vertices.append(p)
    return vertices


def kare_es_1_sargi_kenarlari(n: int) -> list[tuple[int, int]]:
    edges: list[tuple[int, int]] = []
    for i in range(1, n + 1):
        edges.append((i, i + 1))
    start_left = n + 2
    last_index = 2 * n + 1
    for i in range(start_left, last_index):
        edges.append((i, i + 1))
    edges.append((last_index, 0))
    return edges


def hesap_kare_es_1(post):
    W = _f(post, "agiz_en")
    H = _f(post, "agiz_boy")
    L = _f(post, "yukseklik")
    K = _f_opt(post, "kaciklik", 0)
    n = int(_f_opt(post, "egri_bolme_sayisi", 8))
    t = _f(post, "sac_kalinlik_mm")
    vertices = kare_es_1_vertices(H, L, K, n)
    sargi = kare_es_1_sargi_kenarlari(n)
    flans_cm2 = _flans_alani_m2(post, "kare_es_1") * 10000
    return hesap_genel_offset(vertices, sargi, W, fire_orani=0.05, flans_alani_cm2=flans_cm2, sac_kalinligi_mm=t)


def kare_es_2_vertices(H: float, L: float, K: float, duz_sol: float = 0, duz_sag: float = 0) -> list[tuple[float, float]]:
    gecis = L - duz_sol - duz_sag
    if gecis < 0:
        gecis = 0
    x0 = 0.0
    x1 = duz_sol
    x2 = duz_sol + gecis
    x3 = L
    return [
        (x0, K),
        (x0, K + H),
        (x1, K + H),
        (x2, H),
        (x3, H),
        (x3, 0),
        (x2, 0),
        (x1, K),
    ]


kare_es_2_sargi_kenarlari: list[tuple[int, int]] = [
    (1, 2), (2, 3), (3, 4),
    (5, 6), (6, 7), (7, 0),
]


def hesap_kare_es_2(post):
    W = _f(post, "agiz_en")
    H = _f(post, "agiz_boy")
    L = _f(post, "yukseklik")
    K = _f_opt(post, "kaciklik", 0)
    duz_sol = _f_opt(post, "duz_sol", 0)
    duz_sag = _f_opt(post, "duz_sag", 0)
    t = _f(post, "sac_kalinlik_mm")
    vertices = kare_es_2_vertices(H, L, K, duz_sol, duz_sag)
    flans_cm2 = _flans_alani_m2(post, "kare_es_2") * 10000
    return hesap_genel_offset(vertices, kare_es_2_sargi_kenarlari, W, fire_orani=0.05, flans_alani_cm2=flans_cm2, sac_kalinligi_mm=t)


def hesap_kare_pantolon(post):
    ana_en = _f_opt(post, "ana_en", _f(post, "giris_en") if "giris_en" in post else 0)
    ana_boy = _f_opt(post, "ana_boy", _f(post, "yukseklik") if "yukseklik" in post else 0)
    sol_en = _f_opt(post, "sol_en", _f(post, "cikis_en") if "cikis_en" in post else 0)
    sol_boy = _f_opt(post, "sol_boy", _f(post, "cikis_boy") if "cikis_boy" in post else 0)
    sag_en = _f_opt(post, "sag_en", _f(post, "cikis_en") if "cikis_en" in post else 0)
    sag_boy = _f_opt(post, "sag_boy", _f(post, "cikis_boy") if "cikis_boy" in post else 0)
    kanal_derinligi = _f_opt(post, "kanal_derinligi", _f(post, "giris_boy") if "giris_boy" in post else 0)
    r_sol = _f_opt(post, "r_sol", sol_en)
    r_sag = _f_opt(post, "r_sag", sag_en)
    t = _f(post, "sac_kalinlik_mm")
    yay_sol = math.pi * r_sol / 2
    yay_sag = math.pi * r_sag / 2
    govde_cm2 = 2 * (ana_en + kanal_derinligi) * ana_boy
    sol_cm2 = 2 * (sol_en + sol_boy) * yay_sol
    sag_cm2 = 2 * (sag_en + sag_boy) * yay_sag
    flans_cm2 = _flans_alani_m2(post, "kare_pantolon") * 10000.0
    alan_m2 = (govde_cm2 + sol_cm2 + sag_cm2 + flans_cm2) / 10000.0
    return _sonuc(alan_m2, t, 0.10, {"govde_cm2": round(govde_cm2, 2), "sol_dirsek_cm2": round(sol_cm2, 2), "sag_dirsek_cm2": round(sag_cm2, 2), "flans_cm2": round(flans_cm2, 2)})


def hesap_kare_pantolon_2(post):
    ana_en = _f(post, "ana_en")
    derinlik = _f(post, "ana_boy")
    ana_yukseklik = _f(post, "ana_yukseklik")
    kol_en = _f(post, "kol_en")
    kol_boy = _f(post, "kol_boy")
    kol_boyu = _f(post, "kol_boyu")
    r = _f(post, "r")
    if not math.isclose(derinlik, kol_boy, abs_tol=0.01):
        raise ValueError("Kare Pantolon 2'de ana kanal ve yan kol boylari ayni olmali.")

    yay = math.pi * r / 2
    ana_cm2 = 2 * (ana_en + derinlik) * ana_yukseklik
    kol_cm2 = 2 * (kol_en + derinlik) * kol_boyu
    kavis_cm2 = 2 * (kol_en + derinlik) * yay
    flans_cm2 = (2 * (ana_en + derinlik) + 2 * (ana_en + derinlik) + 2 * (kol_en + derinlik)) * FLANS_PAYI_CM
    alan_m2 = (ana_cm2 + kol_cm2 + kavis_cm2 + flans_cm2) / 10000.0
    return _sonuc(alan_m2, _f(post, "sac_kalinlik_mm"), 0.15, {"ana_govde_cm2": round(ana_cm2, 2), "yan_kol_cm2": round(kol_cm2, 2), "kavis_cm2": round(kavis_cm2, 2), "flans_cm2": round(flans_cm2, 2)})


def _istavroz_olcu(post: dict, yeni_anahtar: str, eski_anahtar: str) -> float:
    return _f_opt(post, yeni_anahtar, _f(post, eski_anahtar) if eski_anahtar in post else 0)


def hesap_kare_istavroz(post):
    ust_en = _istavroz_olcu(post, "ust_en", "ana_cikis_en")
    ust_boy = _istavroz_olcu(post, "ust_boy", "ana_cikis_boy")
    alt_en = _istavroz_olcu(post, "alt_en", "ana_giris_en")
    alt_boy = _istavroz_olcu(post, "alt_boy", "ana_giris_boy")
    sol_en = _istavroz_olcu(post, "sol_en", "sol_kol_en")
    sol_boy = _istavroz_olcu(post, "sol_boy", "sol_kol_boy")
    sag_en = _istavroz_olcu(post, "sag_en", "sag_kol_en")
    sag_boy = _istavroz_olcu(post, "sag_boy", "sag_kol_boy")
    boylar = [ust_boy, alt_boy, sol_boy, sag_boy]
    if not all(math.isclose(boy, boylar[0], abs_tol=0.01) for boy in boylar[1:]):
        raise ValueError("Kare istavrozda tum agiz boylari ayni olmali.")

    derinlik = cm_to_m(ust_boy)
    ust_en_m = cm_to_m(ust_en)
    alt_en_m = cm_to_m(alt_en)
    sol_en_m = cm_to_m(sol_en)
    sag_en_m = cm_to_m(sag_en)

    # Yan dirsek R'si kendi kol enidir; ana hat boyu girilen alt-ust gecis mesafesidir.
    ana_hat_boyu = cm_to_m(_f(post, "yukseklik"))
    ana_hat_egik_kenari = math.hypot(ana_hat_boyu, (alt_en_m - ust_en_m) / 2)
    ana_hat_alani = (alt_en_m + ust_en_m) * ana_hat_boyu + 2 * derinlik * ana_hat_egik_kenari
    sol_yay_boyu = math.pi * sol_en_m / 2
    sag_yay_boyu = math.pi * sag_en_m / 2
    sol_dirsek_alani = 2 * (sol_en_m + derinlik) * sol_yay_boyu
    sag_dirsek_alani = 2 * (sag_en_m + derinlik) * sag_yay_boyu
    flans_m2 = _flans_alani_m2(post, "kare_istavroz")
    alan_m2 = ana_hat_alani + sol_dirsek_alani + sag_dirsek_alani + flans_m2
    return _sonuc(alan_m2, _f(post, "sac_kalinlik_mm"), 0.15, {
        "kanal_derinligi_m": round(derinlik, 3),
        "ana_hat_alani_m2": round(ana_hat_alani, 3),
        "sol_dirsek_alani_m2": round(sol_dirsek_alani, 3),
        "sag_dirsek_alani_m2": round(sag_dirsek_alani, 3),
        "flans_m2": round(flans_m2, 3),
    })


def hesap_kare_reduksiyon(post):
    ust_en = cm_to_m(_f(post, "ust_en"))
    ust_boy = cm_to_m(_f(post, "ust_boy"))
    alt_en = cm_to_m(_f(post, "alt_en"))
    alt_boy = cm_to_m(_f(post, "alt_boy"))
    y = cm_to_m(_f(post, "yukseklik"))
    t = _f(post, "sac_kalinlik_mm")
    on_arka_egik_boy = math.hypot(y, (ust_boy - alt_boy) / 2)
    sol_sag_egik_boy = math.hypot(y, (ust_en - alt_en) / 2)
    alan_m2 = (ust_en + alt_en) * on_arka_egik_boy + (ust_boy + alt_boy) * sol_sag_egik_boy
    flans_m2 = _flans_alani_m2(post, "kare_reduksiyon")
    return _sonuc(alan_m2 + flans_m2, t, 0.05, {"on_arka_egik_boy_m": round(on_arka_egik_boy, 3), "sol_sag_egik_boy_m": round(sol_sag_egik_boy, 3)})


def hesap_kare_saplama(post):
    cevre = 2 * (cm_to_m(_f(post, "agiz_en")) + cm_to_m(_f(post, "agiz_boy")))
    boy_m = 0.50
    alan_m2 = cevre * boy_m
    flans_m2 = _flans_alani_m2(post, "kare_saplama")
    return _sonuc(
        alan_m2 + flans_m2,
        _f(post, "sac_kalinlik_mm"),
        0.05,
        {"parca_boyu_cm": 50.0, "govde_alani_m2": round(alan_m2, 3), "flans_m2": round(flans_m2, 3)},
    )


def hesap_kutu(post):
    en = _f(post, "en")
    boy = _f(post, "boy")
    yukseklik = _f(post, "yukseklik")
    cap = _f(post, "cap") / 10.0
    boru_boyu = 15.0
    t = _f(post, "sac_kalinlik_mm")
    kutu_cm2 = 2 * (en * boy) + 2 * (en * yukseklik) + 2 * (boy * yukseklik)
    delik_cm2 = math.pi * (cap / 2) ** 2
    yuvarlak_cm2 = math.pi * cap * boru_boyu
    flans_cm2 = 0.0
    alan_m2 = (kutu_cm2 - delik_cm2 + yuvarlak_cm2) / 10000.0
    return _sonuc(alan_m2, t, 0.15, {"kutu_cm2": round(kutu_cm2, 2), "delik_cm2": round(delik_cm2, 2), "yuvarlak_boru_boyu_cm": boru_boyu, "yuvarlak_boru_cm2": round(yuvarlak_cm2, 2), "flans_cm2": round(flans_cm2, 2)})


def hesap_kare_kapak(post):
    return _sonuc(cm_to_m(_f(post, "en")) * cm_to_m(_f(post, "boy")), _f(post, "sac_kalinlik_mm"), 0.02)


def hesap_kortapa(post):
    cap = mm_to_m(_f(post, "cap")); girme = cm_to_m(15)
    return _sonuc(math.pi * (cap / 2) ** 2 + math.pi * cap * girme, _f(post, "sac_kalinlik_mm"), 0.05)


def hesap_yuvarlak_istavroz(post):
    ana_cap = _f(post, "ana_cap") / 10.0
    ana_boy = _f(post, "ana_boy")
    sol_cap = _f_opt(post, "sol_cap", _f(post, "kol_cap") if "kol_cap" in post else 0) / 10.0
    sol_boy = _f_opt(post, "sol_boy", _f(post, "kol_boy") if "kol_boy" in post else 0)
    sag_cap = _f_opt(post, "sag_cap", _f(post, "kol_cap") if "kol_cap" in post else 0) / 10.0
    sag_boy = _f_opt(post, "sag_boy", _f(post, "kol_boy") if "kol_boy" in post else 0)
    t = _f(post, "sac_kalinlik_mm")
    ana_cm2 = math.pi * ana_cap * ana_boy
    sol_cm2 = math.pi * sol_cap * sol_boy
    sag_cm2 = math.pi * sag_cap * sag_boy
    delik_cm2 = math.pi * (sol_cap / 2) ** 2 + math.pi * (sag_cap / 2) ** 2
    agiz_payi_cm2 = (math.pi * ana_cap * FLANS_PAYI_CM * 2) + (math.pi * sol_cap * FLANS_PAYI_CM) + (math.pi * sag_cap * FLANS_PAYI_CM)
    alan_m2 = (ana_cm2 + sol_cm2 + sag_cm2 - delik_cm2 + agiz_payi_cm2) / 10000.0
    return _sonuc(alan_m2, t, 0.10, {"ana_cm2": round(ana_cm2, 2), "sol_cm2": round(sol_cm2, 2), "sag_cm2": round(sag_cm2, 2), "delik_cm2": round(delik_cm2, 2), "agiz_payi_cm2": round(agiz_payi_cm2, 2)})


def hesap_yuvarlak_mason(post):
    return _sonuc(math.pi * mm_to_m(_f(post, "cap")) * cm_to_m(_f(post, "boy")), _f(post, "sac_kalinlik_mm"), 0.02)


def hesap_spiro_boru(post: dict[str, object]) -> dict:
    d = mm_to_m(_f(post, "cap")); l = _f(post, "uzunluk"); t = _f(post, "sac_kalinlik_mm"); alan_m2 = math.pi * d * l
    return _sonuc(alan_m2, t, 0.05, {"acilim_m2": round(alan_m2, 3)})


def hesap_yuvarlak_dirsek(post: dict[str, object]) -> dict:
    cap_mm = _f(post, "cap")
    d = mm_to_m(cap_mm)
    aci = _f(post, "aci")
    r = 1.5 * d
    t = _f(post, "sac_kalinlik_mm")
    theta = math.pi * aci / 180.0
    cevre = math.pi * d
    yay = r * theta
    alan_m2 = cevre * yay
    kesilen_m2 = (alan_m2 + (4 - 1) * cevre * 0.02 + yay * 0.02) / 0.95
    return {
        "alan_m2": round(alan_m2, 3),
        "kesilen_m2": round(kesilen_m2, 3),
        "kg": round(_kg(kesilen_m2, t), 2),
        "detay": {
            "acilim_m2": round(alan_m2, 3),
            "merkez_hat_radyusu_cm": round(cap_mm * 0.15, 2),
            "r_cap_orani": 1.5,
        },
    }


def hesap_yuvarlak_reduksiyon(post: dict[str, object]) -> dict:
    d1 = mm_to_m(_f(post, "buyuk_cap")); d2 = mm_to_m(_f(post, "kucuk_cap")); h = cm_to_m(_f(post, "boy")); t = _f(post, "sac_kalinlik_mm"); l = math.sqrt(h ** 2 + ((d1 - d2) / 2) ** 2)
    return _sonuc(math.pi * ((d1 + d2) / 2) * l, t, 0.05)


def hesap_yuvarlak_te(post: dict[str, object]) -> dict:
    D_ana = _f(post, "ana_cap") / 10.0
    L_ana = _f(post, "ana_boy")
    D_kol = _f(post, "kol_cap") / 10.0
    t = _f(post, "sac_kalinlik_mm")
    L_kol = L_ana - D_kol
    if L_kol <= 0:
        raise ValueError("Yuvarlak T'de ana govde uzunlugu kol capindan buyuk olmali.")
    ana_cm2 = math.pi * D_ana * L_ana
    kol_cm2 = math.pi * D_kol * L_kol
    delik_cm2 = math.pi * (D_kol / 2) ** 2
    agiz_payi_cm2 = (math.pi * D_ana * FLANS_PAYI_CM * 2) + (math.pi * D_kol * FLANS_PAYI_CM)
    alan_m2 = (ana_cm2 + kol_cm2 - delik_cm2 + agiz_payi_cm2) / 10000.0
    return _sonuc(alan_m2, t, 0.10, {"ana_cm2": round(ana_cm2, 2), "kol_cm2": round(kol_cm2, 2), "kol_boyu_cm": round(L_kol, 2), "delik_cm2": round(delik_cm2, 2), "agiz_payi_cm2": round(agiz_payi_cm2, 2)})


def hesap_kareden_yuvarlaga(post: dict[str, object]) -> dict:
    K_en = _f(post, "kare_en")
    K_boy = _f(post, "kare_boy")
    D = _f(post, "yuvarlak_cap") / 10.0
    H = _f(post, "yukseklik")
    t = _f(post, "sac_kalinlik_mm")
    kare_cevre = 2 * (K_en + K_boy)
    yuvarlak_cevre = math.pi * D
    ortalama_cevre = (kare_cevre + yuvarlak_cevre) / 2
    govde_cm2 = ortalama_cevre * H
    agiz_payi_cm2 = math.pi * D * FLANS_PAYI_CM
    kare_flans_cm2 = kare_cevre * FLANS_PAYI_CM
    net_cm2 = govde_cm2 + agiz_payi_cm2 + kare_flans_cm2
    alan_m2 = net_cm2 / 10000.0
    return _sonuc(alan_m2, t, 0.10, {"govde_cm2": round(govde_cm2, 2), "agiz_payi_cm2": round(agiz_payi_cm2, 2), "kare_flans_cm2": round(kare_flans_cm2, 2)})


def _hesap_sabit(post: dict[str, object]) -> dict:
    return {"alan_m2": 0, "kesilen_m2": 0, "kg": 0}


def hesap_yuvarlak_kelepce(post):
    return _sonuc(math.pi * mm_to_m(_f(post, "cap")) * cm_to_m(15), _f(post, "sac_kalinlik_mm"), 0.02)


def hesap_yuvarlak_klape(post):
    cap_mm = _f(post, "cap")
    if cap_mm <= 4:
        raise ValueError("Yuvarlak klape capi 4 mm'den buyuk olmali.")

    govde_boyu_mm = 200.0 if cap_mm <= 150 else cap_mm + 50.0
    kanat_capi_mm = cap_mm - 4.0
    kanat_sayisi = 1 if cap_mm <= 610 else math.ceil(kanat_capi_mm / 200.0)

    govde_alani_m2 = math.pi * mm_to_m(cap_mm) * mm_to_m(govde_boyu_mm)
    kanat_alani_m2 = math.pi * (mm_to_m(kanat_capi_mm) / 2.0) ** 2
    net_alan_m2 = govde_alani_m2 + kanat_alani_m2

    return _sonuc(net_alan_m2, _f(post, "sac_kalinlik_mm"), 0.05, {
        "govde_boyu_mm": round(govde_boyu_mm, 2),
        "govde_alani_m2": round(govde_alani_m2, 3),
        "kanat_capi_mm": round(kanat_capi_mm, 2),
        "kanat_alani_m2": round(kanat_alani_m2, 3),
        "kanat_sayisi": kanat_sayisi,
    })


def _katalog_alani_m2(katalog: dict[int, tuple[float, float]], cap_mm: float) -> tuple[float, str]:
    caplar = sorted(katalog)

    def alan(cap: int) -> float:
        kalinlik_mm, agirlik_kg = katalog[cap]
        return agirlik_kg / (mm_to_m(kalinlik_mm) * YOGUNLUK)

    if cap_mm <= caplar[0]:
        # Katalog Ø120'den başlıyor; daha küçük çapta benzer geometrinin alanı D² ile ölçeklenir.
        return alan(caplar[0]) * (cap_mm / caplar[0]) ** 2, f"{caplar[0]}-olcekli"
    if cap_mm >= caplar[-1]:
        return alan(caplar[-1]) * (cap_mm / caplar[-1]) ** 2, f"{caplar[-1]}-olcekli"

    for alt, ust in zip(caplar, caplar[1:]):
        if cap_mm == alt:
            return alan(alt), str(alt)
        if alt < cap_mm < ust:
            oran = (cap_mm - alt) / (ust - alt)
            return alan(alt) + (alan(ust) - alan(alt)) * oran, f"{alt}-{ust}"

    return alan(caplar[-1]), str(caplar[-1])


def _jetkap_katalog_alani_m2(cap_mm: float) -> tuple[float, str]:
    return _katalog_alani_m2(JETKAP_KATALOG_AGIRLIKLARI, cap_mm)


def hesap_yuvarlak_jetkap(post):
    cap_mm = _f(post, "cap")
    if cap_mm <= 0:
        raise ValueError("Yuvarlak jetkap capi sifirdan buyuk olmali.")
    katalog_alani_m2, katalog_araligi = _jetkap_katalog_alani_m2(cap_mm)
    return _sonuc(katalog_alani_m2, _f(post, "sac_kalinlik_mm"), 0.05, {
        "katalog_araligi_mm": katalog_araligi,
        "net_sac_alani_m2": round(katalog_alani_m2, 3),
    })


def hesap_yuvarlak_saplama(post):
    cap_mm = _f(post, "cap")
    if cap_mm <= 0:
        raise ValueError("Yuvarlak saplama capi sifirdan buyuk olmali.")
    boy_mm = 200.0
    alan_m2 = math.pi * mm_to_m(cap_mm) * mm_to_m(boy_mm)
    return _sonuc(alan_m2, _f(post, "sac_kalinlik_mm"), 0.05, {
        "boy_mm": round(boy_mm, 2),
        "acilim_m2": round(alan_m2, 3),
    })


def hesap_yuvarlak_sapka(post):
    cap_mm = _f(post, "cap")
    if cap_mm <= 0:
        raise ValueError("Yuvarlak sapka capi sifirdan buyuk olmali.")
    katalog_alani_m2, katalog_araligi = _katalog_alani_m2(SAPKA_KATALOG_AGIRLIKLARI, cap_mm)
    return _sonuc(katalog_alani_m2, _f(post, "sac_kalinlik_mm"), 0.05, {
        "katalog_araligi_mm": katalog_araligi,
        "net_sac_alani_m2": round(katalog_alani_m2, 3),
    })


HESAPLAYICILAR: dict[str, Callable[[dict[str, object]], dict]] = {name.replace("hesap_", ""): func for name, func in list(globals().items()) if name.startswith("hesap_") and callable(func)}


def calculate_geometry(part_code: str, data: dict[str, object]) -> dict:
    try:
        fn = HESAPLAYICILAR[part_code]
    except KeyError as exc:
        raise ValueError(f"Parça hesaplayıcısı bulunamadı: {part_code}") from exc
    return fn(data)
