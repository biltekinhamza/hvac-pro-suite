from __future__ import annotations

from decimal import Decimal
import math


def _d(x: object) -> Decimal:
    return Decimal(str(x).replace(",", "."))


def _mm_to_cm(x: object) -> Decimal:
    return _d(x) / Decimal("10")


def dikdortgen_cevresi_cm(en_cm: object, boy_cm: object) -> Decimal:
    return Decimal("2") * (_d(en_cm) + _d(boy_cm))


def yuvarlak_cevresi_cm(cap_mm: object) -> Decimal:
    return Decimal(str(math.pi)) * _mm_to_cm(cap_mm)


def agizlari_getir(parca_kodu: str, post: dict[str, object]) -> list[tuple]:
    agizlar: list[tuple] = []
    if parca_kodu in {"dikdortgen_kanal", "kare_dirsek", "kare_es_1", "kare_es_2"}:
        en = post.get("agiz_en")
        boy = post.get("agiz_boy")
        agizlar.extend([("dikdortgen", en, boy), ("dikdortgen", en, boy)])
    elif parca_kodu == "kare_pantolon":
        agizlar.extend([("dikdortgen", post.get("ana_en") or post.get("giris_en"), post.get("kanal_derinligi") or post.get("giris_boy")), ("dikdortgen", post.get("sol_en") or post.get("cikis_en"), post.get("sol_boy") or post.get("cikis_boy")), ("dikdortgen", post.get("sag_en") or post.get("cikis_en"), post.get("sag_boy") or post.get("cikis_boy"))])
    elif parca_kodu == "kare_pantolon_2":
        agizlar.extend([("dikdortgen", post.get("ana_en"), post.get("ana_boy")), ("dikdortgen", post.get("ana_en"), post.get("ana_boy")), ("dikdortgen", post.get("kol_en"), post.get("kol_boy"))])
    elif parca_kodu == "kare_istavroz":
        agizlar.extend([("dikdortgen", post.get("alt_en") or post.get("ana_giris_en"), post.get("alt_boy") or post.get("ana_giris_boy")), ("dikdortgen", post.get("ust_en") or post.get("ana_cikis_en"), post.get("ust_boy") or post.get("ana_cikis_boy")), ("dikdortgen", post.get("sol_en") or post.get("sol_kol_en"), post.get("sol_boy") or post.get("sol_kol_boy")), ("dikdortgen", post.get("sag_en") or post.get("sag_kol_en"), post.get("sag_boy") or post.get("sag_kol_boy"))])
    elif parca_kodu == "kare_reduksiyon":
        agizlar.extend([("dikdortgen", post.get("ust_en"), post.get("ust_boy")), ("dikdortgen", post.get("alt_en"), post.get("alt_boy"))])
    elif parca_kodu == "kare_saplama":
        agizlar.append(("dikdortgen", post.get("agiz_en"), post.get("agiz_boy")))
    elif parca_kodu == "spiro_boru":
        cap = post.get("cap")
        agizlar.extend([("yuvarlak", cap), ("yuvarlak", cap)])
    elif parca_kodu == "kareden_yuvarlaga":
        agizlar.extend([("dikdortgen", post.get("kare_en"), post.get("kare_boy")), ("yuvarlak", post.get("yuvarlak_cap"))])
    elif parca_kodu == "kortapa":
        agizlar.append(("yuvarlak", post.get("cap")))
    elif parca_kodu == "yuvarlak_dirsek":
        cap = post.get("cap")
        agizlar.extend([("yuvarlak", cap), ("yuvarlak", cap)])
    elif parca_kodu == "yuvarlak_istavroz":
        agizlar.extend([("yuvarlak", post.get("ana_cap")), ("yuvarlak", post.get("sol_cap") or post.get("kol_cap")), ("yuvarlak", post.get("sag_cap") or post.get("kol_cap"))])
    elif parca_kodu == "yuvarlak_mason":
        cap = post.get("cap")
        agizlar.extend([("yuvarlak", cap), ("yuvarlak", cap)])
    elif parca_kodu == "yuvarlak_reduksiyon":
        agizlar.extend([("yuvarlak", post.get("buyuk_cap")), ("yuvarlak", post.get("kucuk_cap"))])
    elif parca_kodu == "yuvarlak_te":
        agizlar.extend([("yuvarlak", post.get("ana_cap")), ("yuvarlak", post.get("ana_cap")), ("yuvarlak", post.get("kol_cap"))])
    elif parca_kodu == "kutu":
        agizlar.append(("yuvarlak", post.get("cap")))
    return agizlar


def toplam_cevres_cm(agizlar: list[tuple]) -> Decimal:
    toplam = Decimal("0")
    for a in agizlar:
        if a[0] == "dikdortgen":
            toplam += dikdortgen_cevresi_cm(a[1], a[2])
        elif a[0] == "yuvarlak":
            toplam += yuvarlak_cevresi_cm(a[1])
    return toplam


def toplam_cevres_metre(agizlar: list[tuple]) -> Decimal:
    return toplam_cevres_cm(agizlar) / Decimal("100")


def civata_adedi(cap_mm: object) -> int:
    cap = float(str(cap_mm).replace(",", "."))
    tablo = [(160, 6), (200, 8), (250, 8), (315, 10), (355, 12), (400, 12), (450, 14), (500, 16), (630, 20), (800, 24)]
    for limit, adet in tablo:
        if cap <= limit:
            return adet
    return 28


def toplam_civata(agizlar: list[tuple]) -> int:
    toplam = 0
    for a in agizlar:
        if a[0] == "yuvarlak":
            toplam += civata_adedi(a[1])
        elif a[0] == "dikdortgen":
            toplam += 4
    return toplam
