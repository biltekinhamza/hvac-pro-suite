PARTS = {
    "dikdortgen_kanal": {
        "group": "kare",
        "title": "Dikdortgen Kanal",
        "fields": [("agiz_en", "Agiz En (cm)"), ("agiz_boy", "Agiz Boy (cm)"), ("uzunluk", "Uzunluk (m)")],
        "dimension_markers": [
            {"field": "agiz_en", "symbol": "A", "unit": "cm", "line": [48, 78, 92, 68], "label": [72, 82]},
            {"field": "agiz_boy", "symbol": "B", "unit": "cm", "line": [93, 42, 93, 68], "label": [87, 55]},
            {"field": "uzunluk", "symbol": "L", "unit": "m", "line": [7, 27, 92, 42], "label": [51, 28]},
        ],
        "image": "kare/dikdortgen_kanal.png",
    },
    "kare_dirsek": {
        "group": "kare",
        "title": "Kare Dirsek",
        "fields": [("agiz_en", "Agiz En (cm)"), ("agiz_boy", "Agiz Boy (cm)"), ("aci", "Aci (derece)")],
        "dimension_markers": [
            {"field": "agiz_en", "symbol": "A", "unit": "cm", "line": [55, 18, 84, 14], "label": [70, 9]},
            {"field": "agiz_boy", "symbol": "B", "unit": "cm", "line": [84, 14, 82, 61], "label": [91, 38]},
            {
                "field": "aci",
                "symbol": "Açı",
                "unit": "°",
                "line": [45, 48, 45, 68],
                "segments": [[45, 48, 45, 68], [45, 48, 66, 48]],
                "path": "M 45 59 A 11 11 0 0 0 56 48",
                "label": [60, 59],
            },
        ],
        "image": "kare/kare_dirsek.png",
    },
    "kare_reduksiyon": {
        "group": "kare",
        "title": "Kare Reduksiyon",
        "fields": [("ust_en", "Buyuk En (cm)"), ("ust_boy", "Buyuk Boy (cm)"), ("alt_en", "Kucuk En (cm)"), ("alt_boy", "Kucuk Boy (cm)"), ("yukseklik", "Yukseklik (cm)")],
        "dimension_markers": [
            {"field": "ust_en", "symbol": "A1", "unit": "cm", "line": [7, 76, 86, 81], "label": [47, 89]},
            {"field": "ust_boy", "symbol": "B1", "unit": "cm", "line": [86, 81, 91, 69], "label": [93, 75]},
            {"field": "alt_en", "symbol": "A2", "unit": "cm", "line": [29, 41, 66, 41], "label": [48, 34]},
            {"field": "alt_boy", "symbol": "B2", "unit": "cm", "line": [24, 31, 29, 41], "label": [23, 39]},
            {"field": "yukseklik", "symbol": "H", "unit": "cm", "line": [17, 39, 17, 77], "label": [10, 58]},
        ],
        "image": "kare/kare_reduksiyon.png",
    },
    "kare_saplama": {
        "group": "kare",
        "title": "Kare Saplama",
        "fields": [("agiz_en", "Agiz En (cm)"), ("agiz_boy", "Agiz Boy (cm)")],
        "dimension_markers": [
            {"field": "agiz_en", "symbol": "A", "unit": "cm", "line": [24, 73, 74, 80], "label": [49, 87]},
            {"field": "agiz_boy", "symbol": "B", "unit": "cm", "line": [74, 80, 78, 73], "label": [83, 77]},
        ],
        "image": "kare/kare_saplama.png",
    },
    "kare_es_1": {
        "group": "kare",
        "title": "Kare ES 1 (Egrili S)",
        "fields": [("agiz_en", "Agiz En / Sargi Genisligi (cm)"), ("agiz_boy", "Agiz Boy / Yanak Yukseklik (cm)"), ("yukseklik", "Yukseklik / Profil Boyu (cm)"), ("kaciklik", "Kaciklik (cm)")],
        "dimension_markers": [
            {"field": "agiz_en", "symbol": "A", "unit": "cm", "line": [38, 11, 75, 11], "label": [57, 5]},
            {"field": "agiz_boy", "symbol": "B", "unit": "cm", "line": [38, 11, 46, 15], "label": [40, 19]},
            {"field": "yukseklik", "symbol": "H", "unit": "cm", "line": [22, 17, 22, 83], "label": [14, 50]},
            {
                "field": "kaciklik",
                "symbol": "Kaçıklık",
                "unit": "cm",
                "line": [42, 69, 56, 69],
                "segments": [[42, 64, 42, 74], [42, 69, 56, 69], [56, 64, 56, 74]],
                "label": [49, 80],
            },
        ],
        "image": "kare/kare_es_1.png",
    },
    "kare_es_2": {
        "group": "kare",
        "title": "Kare ES 2 (Kirikli Z)",
        "fields": [("agiz_en", "Agiz En / Sargi Genisligi (cm)"), ("agiz_boy", "Agiz Boy / Yanak Yukseklik (cm)"), ("yukseklik", "Yukseklik / Profil Boyu (cm)"), ("kaciklik", "Kaciklik (cm)"), ("duz_sol", "Sol Duz Bogaz Boyu (cm)"), ("duz_sag", "Sag Duz Bogaz Boyu (cm)")],
        "dimension_markers": [
            {"field": "agiz_en", "symbol": "A", "unit": "cm", "line": [29, 10, 48, 14], "label": [38, 6]},
            {"field": "agiz_boy", "symbol": "B", "unit": "cm", "line": [29, 10, 29, 42], "label": [23, 26]},
            {"field": "yukseklik", "symbol": "H", "unit": "cm", "line": [72, 14, 72, 85], "label": [79, 49]},
            {"field": "kaciklik", "symbol": "K", "unit": "cm", "line": [39, 90, 69, 90], "label": [54, 93]},
            {"field": "duz_sol", "symbol": "L1", "unit": "cm", "line": [48, 14, 48, 43], "label": [53, 29]},
            {"field": "duz_sag", "symbol": "L2", "unit": "cm", "line": [69, 50, 69, 85], "label": [64, 68]},
        ],
        "image": "kare/kare_es_2.png",
    },
    "kare_pantolon": {
        "group": "kare",
        "title": "Kare Pantolon",
        "fields": [("ana_en", "Alt Ana Giris En (cm)"), ("kanal_derinligi", "Alt Ana Giris Derinligi (cm)"), ("ana_boy", "Ana Govde Yuksekligi (cm)"), ("sol_en", "Sol Cikis En (cm)"), ("sol_boy", "Sol Cikis Boy (cm)"), ("sag_en", "Sag Cikis En (cm)"), ("sag_boy", "Sag Cikis Boy (cm)")],
        "equal_arm_pairs": [("sol_en", "sag_en"), ("sol_boy", "sag_boy")],
        "dimension_markers": [
            {"field": "ana_en", "symbol": "A", "unit": "cm", "line": [16, 76, 61, 77], "label": [38, 84]},
            {"field": "kanal_derinligi", "symbol": "B", "unit": "cm", "line": [61, 77, 80, 71], "label": [72, 81]},
            {"field": "ana_boy", "symbol": "H", "unit": "cm", "line": [39, 20, 39, 76], "label": [45, 48]},
            {"field": "sol_en", "symbol": "C", "unit": "cm", "line": [7, 23, 31, 20], "label": [19, 15]},
            {"field": "sol_boy", "symbol": "D", "unit": "cm", "line": [7, 23, 9, 54], "label": [14, 39]},
            {"field": "sag_en", "symbol": "E", "unit": "cm", "line": [72, 31, 92, 26], "label": [83, 20]},
            {"field": "sag_boy", "symbol": "F", "unit": "cm", "line": [92, 26, 92, 60], "label": [85, 44]},
        ],
        "image": "kare/kare_pantolon.png",
    },
    "kare_pantolon_2": {
        "group": "kare",
        "title": "Kare Pantolon 2 (Tek Kol)",
        "fields": [("ana_en", "Ana Kanal En (cm)"), ("ana_boy", "Ana Kanal Boy / Derinlik (cm)"), ("ana_yukseklik", "Ana Kanal Yukseklik (cm)"), ("kol_en", "Yan Kol En (cm)"), ("kol_boy", "Yan Kol Boy / Derinlik (cm)"), ("kol_boyu", "Yan Kol Cikis Boyu (cm)"), ("r", "Kol Donus Radyusu (cm)")],
        "dimension_markers": [
            {"field": "ana_en", "symbol": "A", "unit": "cm", "line": [23, 5, 55, 5], "label": [39, 8]},
            {"field": "ana_boy", "symbol": "B", "unit": "cm", "line": [55, 5, 52, 11], "label": [60, 8]},
            {"field": "ana_yukseklik", "symbol": "H", "unit": "cm", "line": [23, 5, 23, 93], "label": [16, 50]},
            {"field": "kol_en", "symbol": "C", "unit": "cm", "line": [59, 31, 75, 27], "label": [68, 22]},
            {"field": "kol_boy", "symbol": "D", "unit": "cm", "line": [75, 27, 75, 75], "label": [82, 51]},
            {"field": "kol_boyu", "symbol": "L", "unit": "cm", "line": [50, 55, 75, 55], "label": [63, 62]},
            {"field": "r", "symbol": "R", "unit": "cm", "line": [35, 52, 51, 30], "label": [40, 38]},
        ],
        "image": "kare/kare_pantolon_2.png",
    },
    "kare_istavroz": {
        "group": "kare",
        "title": "Kare Istavroz",
        "fields": [("alt_en", "Alt Ana Giris En (cm)"), ("alt_boy", "Alt Ana Giris Boy (cm)"), ("ust_en", "Ust Cikis En (cm)"), ("ust_boy", "Ust Cikis Boy (cm)"), ("sol_en", "Sol Kol En (cm)"), ("sol_boy", "Sol Kol Boy (cm)"), ("sag_en", "Sag Kol En (cm)"), ("sag_boy", "Sag Kol Boy (cm)"), ("yukseklik", "Ana Hat Gecis Boyu (cm)")],
        "equal_arm_pairs": [("sol_en", "sag_en"), ("sol_boy", "sag_boy")],
        "dimension_markers": [
            {"field": "alt_en", "symbol": "A1", "unit": "cm", "line": [32, 87, 79, 82], "label": [56, 92]},
            {"field": "alt_boy", "symbol": "B1", "unit": "cm", "line": [21, 74, 32, 87], "label": [22, 84]},
            {"field": "ust_en", "symbol": "A2", "unit": "cm", "line": [41, 28, 72, 23], "label": [57, 18]},
            {"field": "ust_boy", "symbol": "B2", "unit": "cm", "line": [28, 19, 41, 28], "label": [35, 14]},
            {"field": "sol_en", "symbol": "C", "unit": "cm", "line": [6, 24, 8, 66], "label": [6, 46]},
            {"field": "sol_boy", "symbol": "D", "unit": "cm", "line": [6, 24, 14, 34], "label": [12, 19]},
            {"field": "sag_en", "symbol": "E", "unit": "cm", "line": [93, 25, 91, 54], "label": [95, 40]},
            {"field": "sag_boy", "symbol": "F", "unit": "cm", "line": [79, 17, 93, 25], "label": [88, 13]},
            {"field": "yukseklik", "symbol": "H", "unit": "cm", "line": [50, 28, 50, 86], "label": [56, 57]},
        ],
        "image": "kare/kare_istavroz.png",
    },
    "kutu": {
        "group": "kare",
        "title": "Kutu",
        "fields": [("en", "En (cm)"), ("boy", "Boy (cm)"), ("yukseklik", "Yukseklik (cm)"), ("cap", "Cikis Capi (mm)")],
        "dimension_markers": [
            {"field": "en", "symbol": "A", "unit": "cm", "line": [10, 27, 71, 15], "label": [40, 10]},
            {"field": "boy", "symbol": "B", "unit": "cm", "line": [71, 15, 93, 32], "label": [86, 18]},
            {"field": "yukseklik", "symbol": "H", "unit": "cm", "line": [10, 27, 10, 59], "label": [5, 44]},
            {"field": "cap", "symbol": "ØD", "unit": "mm", "line": [83, 43, 83, 74], "label": [91, 59]},
        ],
        "image": "kare/kutu.png",
    },
    "kare_kapak": {
        "group": "kare",
        "title": "Kare Kapak",
        "fields": [("en", "En (cm)"), ("boy", "Boy (cm)")],
        "dimension_markers": [
            {"field": "en", "symbol": "A", "unit": "cm", "line": [16, 20, 84, 10], "label": [50, 5]},
            {"field": "boy", "symbol": "B", "unit": "cm", "line": [15, 20, 15, 85], "label": [8, 52]},
        ],
        "image": "kare/kare_kapak.png",
    },
    "spiro_boru": {
        "group": "yuvarlak",
        "title": "Spiro Boru",
        "fields": [("cap", "Cap (mm)"), ("uzunluk", "Uzunluk (m)")],
        "dimension_markers": [
            {"field": "cap", "symbol": "ØD", "unit": "mm", "line": [21, 54, 21, 86], "label": [10, 70]},
            {"field": "uzunluk", "symbol": "L", "unit": "m", "line": [25, 55, 85, 23], "label": [57, 33]},
        ],
        "image": "yuvarlak/spiro_boru.png",
    },
    "yuvarlak_dirsek": {
        "group": "yuvarlak",
        "title": "Yuvarlak Dirsek",
        "fields": [("cap", "Cap (mm)"), ("aci", "Aci (derece)"), ("r", "Merkez Hat Radyusu R (cm)")],
        "computed_fields": [
            {"field": "r", "source": "cap", "factor": 0.15, "decimals": 2},
        ],
        "dimension_markers": [
            {"field": "cap", "symbol": "ØD", "unit": "mm", "line": [66, 17, 66, 57], "label": [77, 37]},
            {
                "field": "aci",
                "symbol": "Açı",
                "unit": "°",
                "line": [41, 45, 41, 67],
                "segments": [[41, 45, 41, 67], [41, 45, 63, 45]],
                "path": "M 41 57 A 12 12 0 0 0 53 45",
                "label": [57, 59],
            },
            {"field": "r", "symbol": "R", "unit": "cm", "line": [42, 39, 58, 55], "label": [50, 34]},
        ],
        "image": "yuvarlak/yuvarlak_dirsek.png",
    },
    "kareden_yuvarlaga": {
        "group": "yuvarlak",
        "title": "Kareden Yuvarlaga",
        "fields": [("kare_en", "Alt Agiz En (cm)"), ("kare_boy", "Alt Agiz Boy (cm)"), ("yuvarlak_cap", "Ust Agiz Capi (mm)"), ("yukseklik", "Gecis Boyu (cm)")],
        "dimension_markers": [
            {"field": "kare_en", "symbol": "A", "unit": "cm", "line": [22, 77, 75, 84], "label": [49, 92]},
            {"field": "kare_boy", "symbol": "B", "unit": "cm", "line": [75, 84, 79, 72], "label": [83, 78]},
            {"field": "yuvarlak_cap", "symbol": "ØD", "unit": "mm", "line": [36, 12, 64, 12], "label": [50, 6]},
            {"field": "yukseklik", "symbol": "H", "unit": "cm", "line": [22, 27, 22, 77], "label": [14, 52]},
        ],
        "image": "yuvarlak/kareden_yuvarlaga.png",
    },
    "kortapa": {
        "group": "yuvarlak",
        "title": "Kortapa",
        "fields": [("cap", "Cap (mm)")],
        "dimension_markers": [
            {"field": "cap", "symbol": "ØD", "unit": "mm", "line": [31, 27, 31, 82], "label": [22, 54]},
        ],
        "image": "yuvarlak/kortapa.png",
    },
    "yuvarlak_istavroz": {
        "group": "yuvarlak",
        "title": "Yuvarlak Istavroz",
        "fields": [("ana_cap", "Ana Cap (mm)"), ("ana_boy", "Ana Boy (cm)"), ("sol_cap", "Sol Kol Capi (mm)"), ("sol_boy", "Sol Kol Boyu (cm)"), ("sag_cap", "Sag Kol Capi (mm)"), ("sag_boy", "Sag Kol Boyu (cm)")],
        "equal_arm_pairs": [("sol_cap", "sag_cap"), ("sol_boy", "sag_boy")],
        "marker_display": "focus",
        "dimension_markers": [
            {"field": "ana_cap", "symbol": "ØA", "unit": "mm", "line": [36, 25, 70, 25], "label": [53, 17]},
            {"field": "ana_boy", "symbol": "L", "unit": "cm", "line": [71, 25, 71, 93], "label": [77, 60]},
            {"field": "sol_cap", "symbol": "ØB", "unit": "mm", "line": [22, 48, 22, 73], "label": [13, 61]},
            {"field": "sol_boy", "symbol": "L1", "unit": "cm", "line": [22, 59, 42, 59], "label": [32, 52]},
            {"field": "sag_cap", "symbol": "ØC", "unit": "mm", "line": [83, 47, 83, 70], "label": [91, 58]},
            {"field": "sag_boy", "symbol": "L2", "unit": "cm", "line": [69, 58, 83, 58], "label": [77, 52]},
        ],
        "image": "yuvarlak/yuvarlak_istavroz.png",
    },
    "yuvarlak_mason": {
        "group": "yuvarlak",
        "title": "Yuvarlak Manson",
        "fields": [("cap", "Cap (mm)"), ("boy", "Boy (cm)")],
        "dimension_markers": [
            {"field": "cap", "symbol": "ØD", "unit": "mm", "line": [27, 20, 27, 78], "label": [17, 49]},
            {"field": "boy", "symbol": "L", "unit": "cm", "line": [54, 16, 69, 22], "label": [64, 10]},
        ],
        "image": "yuvarlak/yuvarlak_mason.png",
    },
    "yuvarlak_reduksiyon": {
        "group": "yuvarlak",
        "title": "Yuvarlak Reduksiyon",
        "fields": [("buyuk_cap", "Buyuk Cap (mm)"), ("kucuk_cap", "Kucuk Cap (mm)"), ("boy", "Boy (cm)")],
        "dimension_markers": [
            {"field": "buyuk_cap", "symbol": "ØA", "unit": "mm", "line": [21, 78, 75, 78], "label": [48, 87]},
            {"field": "kucuk_cap", "symbol": "ØB", "unit": "mm", "line": [33, 14, 63, 14], "label": [48, 7]},
            {"field": "boy", "symbol": "L", "unit": "cm", "line": [78, 22, 78, 78], "label": [86, 50]},
        ],
        "image": "yuvarlak/yuvarlak_reduksiyon.png",
    },
    "yuvarlak_te": {
        "group": "yuvarlak",
        "title": "Yuvarlak T",
        "fields": [("ana_cap", "Ana Cap (mm)"), ("kol_cap", "Kol Capi (mm)"), ("ana_boy", "Ana Govde Uzunlugu (cm)")],
        "dimension_markers": [
            {"field": "ana_cap", "symbol": "ØA", "unit": "mm", "line": [24, 12, 55, 12], "label": [39, 5]},
            {"field": "kol_cap", "symbol": "ØB", "unit": "mm", "line": [75, 39, 75, 76], "label": [84, 58]},
            {"field": "ana_boy", "symbol": "L", "unit": "cm", "line": [20, 8, 20, 95], "label": [12, 52]},
        ],
        "image": "yuvarlak/yuvarlak_te.png",
    },
    "yuvarlak_kelepce": {
        "group": "yuvarlak",
        "title": "Yuvarlak Kelepce",
        "fields": [("cap", "Cap (mm)")],
        "dimension_markers": [
            {"field": "cap", "symbol": "ØD", "unit": "mm", "line": [16, 47, 83, 58], "label": [50, 67]},
        ],
        "image": "yuvarlak/yuvarlak_kelepce.png",
    },
    "yuvarlak_klape": {
        "group": "yuvarlak",
        "title": "Yuvarlak Klape",
        "fields": [("cap", "Cap (mm)")],
        "dimension_markers": [
            {"field": "cap", "symbol": "ØD", "unit": "mm", "line": [70, 30, 70, 78], "label": [81, 54]},
        ],
        "image": "yuvarlak/yuvarlak_klape.png",
    },
    "yuvarlak_jetkap": {
        "group": "yuvarlak",
        "title": "Yuvarlak Jetkap",
        "fields": [("cap", "Cap (mm)")],
        "dimension_markers": [
            {"field": "cap", "symbol": "ØD", "unit": "mm", "line": [34, 74, 67, 74], "label": [50, 83]},
        ],
        "image": "yuvarlak/yuvarlak_jetkap.png",
    },
    "yuvarlak_saplama": {
        "group": "yuvarlak",
        "title": "Yuvarlak Saplama",
        "fields": [("cap", "Cap (mm)")],
        "dimension_markers": [
            {"field": "cap", "symbol": "ØD", "unit": "mm", "line": [28, 13, 72, 13], "label": [50, 7]},
        ],
        "image": "yuvarlak/yuvarlak_saplama.png",
    },
    "yuvarlak_sapka": {
        "group": "yuvarlak",
        "title": "Yuvarlak Sapka",
        "fields": [("cap", "Cap (mm)")],
        "dimension_markers": [
            {"field": "cap", "symbol": "ØD", "unit": "mm", "line": [31, 76, 69, 76], "label": [50, 85]},
        ],
        "image": "yuvarlak/yuvarlak_sapka.png",
    },
}


def list_parts() -> list[dict]:
    return [
        {
            "code": code,
            "group": cfg["group"],
            "title": cfg["title"],
            "image": cfg.get("image"),
            "fields": [{"name": name, "label": label} for name, label in cfg["fields"]],
            "equal_arm_pairs": [
                {"source": source, "target": target}
                for source, target in cfg.get("equal_arm_pairs", [])
            ],
            "dimension_markers": cfg.get("dimension_markers", []),
            "marker_display": cfg.get("marker_display", "focus"),
            "computed_fields": cfg.get("computed_fields", []),
        }
        for code, cfg in PARTS.items()
    ]
