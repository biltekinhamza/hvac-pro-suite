import sqlite3
import json
import os
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
)

FONT_PATHS = (
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)

TEAL_DARK = colors.HexColor("#134e4a")
TEAL = colors.HexColor("#0f766e")
TEAL_LIGHT = colors.HexColor("#ccfbf1")
SLATE = colors.HexColor("#1e293b")
SLATE_MUTED = colors.HexColor("#64748b")
BORDER = colors.HexColor("#cbd5e1")
ROW_ALT = colors.HexColor("#f8fafc")
RED_LIGHT = colors.HexColor("#fee2e2")
RED = colors.HexColor("#dc2626")
GREEN_LIGHT = colors.HexColor("#dcfce7")
GREEN = colors.HexColor("#16a34a")
BLUE_LIGHT = colors.HexColor("#dbeafe")
BLUE = colors.HexColor("#2563eb")


def _register_font():
    for path in FONT_PATHS:
        if os.path.isfile(path):
            font_name = "CompFont"
            if font_name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(font_name, path))
            return font_name
    return "Helvetica"


def _decimal(value):
    return Decimal(str(value or 0))


def _fmt(value):
    amount = f"{float(value or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{amount} TL"


def _fmt_short(value):
    amount = f"{float(value or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return amount


def _diff_pct(v99, v101):
    a = float(v99 or 0)
    b = float(v101 or 0)
    if a == 0:
        return "+∞" if b > 0 else "0%"
    diff = ((b - a) / a) * 100
    return f"%{diff:+.1f}"


def _diff_abs(v99, v101):
    return float(v101 or 0) - float(v99 or 0)


def _parse_inputs(item):
    try:
        return json.loads(item["inputs_json"] or "{}")
    except Exception:
        return {}


def _build_description(item):
    inputs = _parse_inputs(item)
    parts = []
    part_code = item["part_code"]

    if part_code == "yuvarlak_dirsek":
        parts.append(f"Capi: {inputs.get('cap', '?')} mm")
        parts.append(f"Acisi: {inputs.get('aci', '?')}")
        parts.append(f"Sac: {inputs.get('sac_kalinlik_mm', '?')} mm")
    elif part_code == "kutu":
        parts.append(f"En: {inputs.get('en', '?')} Boy: {inputs.get('boy', '?')} Y: {inputs.get('yukseklik', '?')}")
        parts.append(f"Capi: {inputs.get('cap', '?')} mm")
        parts.append(f"Sac: {inputs.get('sac_kalinlik_mm', '?')} mm")
    elif part_code == "dikdortgen_kanal":
        parts.append(f"Agiz: {inputs.get('agiz_en', '?')}x{inputs.get('agiz_boy', '?')}")
        parts.append(f"Uzunluk: {inputs.get('uzunluk', '?')} m")
        parts.append(f"Sac: {inputs.get('sac_kalinlik_mm', '?')} mm")
    elif part_code == "kare_dirsek":
        parts.append(f"Agiz: {inputs.get('agiz_en', '?')}x{inputs.get('agiz_boy', '?')}")
        parts.append(f"Acisi: {inputs.get('aci', '?')}")
        parts.append(f"Sac: {inputs.get('sac_kalinlik_mm', '?')} mm")
    elif part_code == "kare_reduksiyon":
        parts.append(f"Ust: {inputs.get('ust_en', '?')}x{inputs.get('ust_boy', '?')}")
        parts.append(f"Alt: {inputs.get('alt_en', '?')}x{inputs.get('alt_boy', '?')}")
        parts.append(f"Yukseklik: {inputs.get('yukseklik', '?')}")
        parts.append(f"Sac: {inputs.get('sac_kalinlik_mm', '?')} mm")
    elif part_code == "yuvarlak_saplama":
        parts.append(f"Capi: {inputs.get('cap', '?')} mm")
        parts.append(f"Boy: {inputs.get('boy', '?')} mm")
        parts.append(f"Sac: {inputs.get('sac_kalinlik_mm', '?')} mm")

    ins = inputs.get("izolasyon_ozellik_id", "")
    if ins and ins not in ("", "false", "0"):
        parts.append("Izolasyonlu")

    return " | ".join(parts)


def _group_items(items):
    groups = {}
    for item in items:
        key = item["part_code"]
        if key not in groups:
            groups[key] = []
        groups[key].append(item)
    return groups


def build_comparison_pdf(quote99, items99, quote101, items101, output_path):
    font_name = _register_font()

    groups99 = _group_items(items99)
    groups101 = _group_items(items101)
    all_codes = list(dict.fromkeys(list(groups99.keys()) + list(groups101.keys())))

    total99 = sum(float(i["line_total"] or 0) for i in items99)
    total101 = sum(float(i["line_total"] or 0) for i in items101)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"Teklif Kiyaslama #{quote99['id']} vs #{quote101['id']}",
        author="HVAC Pro Suite",
    )

    s = _styles(font_name)
    story = []

    story.extend(_build_header(quote99, quote101, s, font_name, total99, total101))

    for code in all_codes:
        g99 = groups99.get(code, [])
        g101 = groups101.get(code, [])
        story.extend(_build_group_table(code, g99, g101, s, font_name))

    story.extend(_build_summary_table(items99, items101, total99, total101, s))

    doc.build(story)
    return output_path


def _styles(font_name):
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title2", parent=base["Title"], fontName=font_name, fontSize=18, leading=22,
            textColor=TEAL_DARK,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle2", parent=base["BodyText"], fontName=font_name, fontSize=10, leading=14,
            textColor=SLATE_MUTED,
        ),
        "groupTitle": ParagraphStyle(
            "GroupTitle", parent=base["Heading2"], fontName=font_name, fontSize=12, leading=16,
            textColor=TEAL_DARK,
        ),
        "hdr": ParagraphStyle(
            "Hdr", parent=base["BodyText"], fontName=font_name, fontSize=7.5, leading=10,
            textColor=colors.white,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontName=font_name, fontSize=7.5, leading=10,
            textColor=SLATE,
        ),
        "right": ParagraphStyle(
            "Right", parent=base["BodyText"], fontName=font_name, fontSize=7.5, leading=10,
            textColor=SLATE, alignment=TA_RIGHT,
        ),
        "center": ParagraphStyle(
            "Center", parent=base["BodyText"], fontName=font_name, fontSize=7.5, leading=10,
            textColor=SLATE, alignment=TA_CENTER,
        ),
        "diff_pos": ParagraphStyle(
            "DiffPos", parent=base["BodyText"], fontName=font_name, fontSize=7.5, leading=10,
            textColor=RED,
        ),
        "diff_neg": ParagraphStyle(
            "DiffNeg", parent=base["BodyText"], fontName=font_name, fontSize=7.5, leading=10,
            textColor=GREEN,
        ),
        "totLabel": ParagraphStyle(
            "TotLabel", parent=base["BodyText"], fontName=font_name, fontSize=9, leading=13,
            textColor=SLATE,
        ),
        "totValue": ParagraphStyle(
            "TotValue", parent=base["BodyText"], fontName=font_name, fontSize=9, leading=13,
            textColor=SLATE, alignment=TA_RIGHT,
        ),
        "grandLabel": ParagraphStyle(
            "GrandLabel", parent=base["BodyText"], fontName=font_name, fontSize=10, leading=14,
            textColor=TEAL_DARK,
        ),
        "grandValue": ParagraphStyle(
            "GrandValue", parent=base["BodyText"], fontName=font_name, fontSize=10, leading=14,
            textColor=TEAL_DARK, alignment=TA_RIGHT,
        ),
        "meta": ParagraphStyle(
            "Meta", parent=base["BodyText"], fontName=font_name, fontSize=8, leading=11,
            textColor=SLATE_MUTED,
        ),
        "metaVal": ParagraphStyle(
            "MetaVal", parent=base["BodyText"], fontName=font_name, fontSize=9, leading=12,
            textColor=SLATE,
        ),
    }


def _cell_pad(top=2, bottom=2, left=4, right=4):
    return TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), top),
        ("BOTTOMPADDING", (0, 0), (-1, -1), bottom),
        ("LEFTPADDING", (0, 0), (-1, -1), left),
        ("RIGHTPADDING", (0, 0), (-1, -1), right),
    ])


def _build_header(q99, q101, s, font_name, total99, total101):
    title = Paragraph("<b>TEKLIF KIYASLAMA RAPORU</b>", s["title"])
    subtitle = Paragraph(
        f"Teklif #{q99['id']} vs Teklif #{q101['id']} | Musteri: {_safe(q99.get('customer_name', ''))}",
        s["subtitle"],
    )

    meta_rows = [
        [
            Paragraph("<b>#99 Bilgileri</b>", s["meta"]),
            Paragraph("", s["meta"]),
            Paragraph("<b>#101 Bilgileri</b>", s["meta"]),
            Paragraph("", s["meta"]),
        ],
        [
            Paragraph("Tarih:", s["meta"]),
            Paragraph(_safe(q99.get("created_at", ""))[:10], s["metaVal"]),
            Paragraph("Tarih:", s["meta"]),
            Paragraph(_safe(q101.get("created_at", ""))[:10], s["metaVal"]),
        ],
        [
            Paragraph("Parca Sayisi:", s["meta"]),
            Paragraph(str(len([i for i in json.loads("[]") or []]) or q99.get("id", "")), s["metaVal"]),
            Paragraph("Parca Sayisi:", s["meta"]),
            Paragraph(str(q101.get("id", "")), s["metaVal"]),
        ],
        [
            Paragraph("Kari Orani:", s["meta"]),
            Paragraph(f"%{q99.get('profit_rate', 0)}", s["metaVal"]),
            Paragraph("Kari Orani:", s["meta"]),
            Paragraph(f"%{q101.get('profit_rate', 0)}", s["metaVal"]),
        ],
        [
            Paragraph("Toplam:", s["meta"]),
            Paragraph(f"<b>{_fmt(total99)}</b>", s["metaVal"]),
            Paragraph("Toplam:", s["meta"]),
            Paragraph(f"<b>{_fmt(total101)}</b>", s["metaVal"]),
        ],
    ]

    meta = Table(meta_rows, colWidths=[30 * mm, 55 * mm, 30 * mm, 55 * mm])
    meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (1, 0), colors.HexColor("#e0f2f1")),
        ("BACKGROUND", (2, 0), (3, 0), colors.HexColor("#e3f2fd")),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("SPAN", (0, 0), (1, 0)),
        ("SPAN", (2, 0), (3, 0)),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    diff_total = _diff_abs(total99, total101)
    diff_pct = _diff_pct(total99, total101)
    sign = "+" if diff_total >= 0 else ""
    diff_color = RED if diff_total > 0 else GREEN if diff_total < 0 else SLATE

    summary = Table(
        [[
            Paragraph("<b>Fiyat Farki:</b>", s["totLabel"]),
            Paragraph(f"<b>{sign}{_fmt(diff_total)}  ({diff_pct})</b>", s["grandValue"]),
        ]],
        colWidths=[40 * mm, 80 * mm],
        hAlign="RIGHT",
    )
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TEAL_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.8, TEAL),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))

    return [title, subtitle, Spacer(1, 4 * mm), meta, Spacer(1, 4 * mm), summary, Spacer(1, 6 * mm)]


def _safe(val):
    return str(val or "").replace("\ufffd", "o").replace("\u00f6", "o").replace("\u00fc", "u").replace("\u0131", "i").replace("\u015f", "s").replace("\u00e7", "c").replace("\u011f", "g")


def _build_group_table(code, items99, items101, s, font_name):
    display_names = {
        "yuvarlak_dirsek": "Yuvarlak Dirsek",
        "kutu": "Kutu",
        "dikdortgen_kanal": "Dikdortgen Kanal",
        "kare_dirsek": "Kare Dirsek",
        "kare_reduksiyon": "Kare Reduksiyon",
        "yuvarlak_saplama": "Yuvarlak Saplama",
    }
    group_name = display_names.get(code, code)

    header_row = [
        Paragraph("<b>Aciklama</b>", s["hdr"]),
        Paragraph("<b>#99 Miktar</b>", s["hdr"]),
        Paragraph("<b>#99 Birim</b>", s["hdr"]),
        Paragraph("<b>#99 Tutar</b>", s["hdr"]),
        Paragraph("<b>#101 Miktar</b>", s["hdr"]),
        Paragraph("<b>#101 Birim</b>", s["hdr"]),
        Paragraph("<b>#101 Tutar</b>", s["hdr"]),
        Paragraph("<b>Fark (TL)</b>", s["hdr"]),
        Paragraph("<b>Fark (%)</b>", s["hdr"]),
    ]

    rows = [header_row]
    group_total_99 = 0
    group_total_101 = 0

    max_len = max(len(items99), len(items101))
    for idx in range(max_len):
        i99 = items99[idx] if idx < len(items99) else None
        i101 = items101[idx] if idx < len(items101) else None

        desc99 = _build_description(i99) if i99 else "-"
        desc101 = _build_description(i101) if i101 else "-"
        desc = desc99 if desc99 == desc101 else f"{desc99}<br/><font size='6' color='#2563eb'>vs {desc101}</font>"

        q99 = i99["quantity"] if i99 else "-"
        q101 = i101["quantity"] if i101 else "-"

        up99 = _fmt_short(i99["unit_price"]) if i99 else "-"
        up101 = _fmt_short(i101["unit_price"]) if i101 else "-"

        lt99 = float(i99["line_total"] or 0) if i99 else 0
        lt101 = float(i101["line_total"] or 0) if i101 else 0
        group_total_99 += lt99
        group_total_101 += lt101

        diff = lt101 - lt99
        diff_s = _diff_pct(lt99, lt101)

        if diff > 0.01:
            diff_style = s["diff_pos"]
            diff_bg = RED_LIGHT
        elif diff < -0.01:
            diff_style = s["diff_neg"]
            diff_bg = GREEN_LIGHT
        else:
            diff_style = s["right"]
            diff_bg = colors.white

        rows.append([
            Paragraph(desc, s["body"]),
            Paragraph(str(q99), s["center"]),
            Paragraph(up99, s["right"]),
            Paragraph(_fmt_short(lt99) if lt99 else "-", s["right"]),
            Paragraph(str(q101), s["center"]),
            Paragraph(up101, s["right"]),
            Paragraph(_fmt_short(lt101) if lt101 else "-", s["right"]),
            Paragraph(f"{('+' if diff >= 0 else '')}{_fmt_short(diff)}", diff_style),
            Paragraph(diff_s, diff_style),
        ])

    grp_diff = group_total_101 - group_total_99
    grp_sign = "+" if grp_diff >= 0 else ""
    rows.append([
        Paragraph(f"<b>{group_name} Alt Toplam</b>", s["body"]),
        Paragraph("", s["center"]),
        Paragraph("", s["right"]),
        Paragraph(f"<b>{_fmt_short(group_total_99)}</b>", s["right"]),
        Paragraph("", s["center"]),
        Paragraph("", s["right"]),
        Paragraph(f"<b>{_fmt_short(group_total_101)}</b>", s["right"]),
        Paragraph(f"<b>{grp_sign}{_fmt_short(grp_diff)}</b>", s["right"]),
        Paragraph(f"<b>{_diff_pct(group_total_99, group_total_101)}</b>", s["right"]),
    ])

    col_widths = [52 * mm, 14 * mm, 20 * mm, 22 * mm, 14 * mm, 20 * mm, 22 * mm, 22 * mm, 16 * mm]
    table = Table(rows, repeatRows=1, colWidths=col_widths)

    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), TEAL_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
        ("LINEBELOW", (0, 0), (-1, 0), 1, TEAL),
        ("INNERGRID", (0, 1), (-1, -1), 0.2, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, ROW_ALT]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, SLATE_MUTED),
        ("ALIGN", (1, 1), (2, -1), "CENTER"),
        ("ALIGN", (4, 1), (5, -1), "CENTER"),
    ]

    for row_idx in range(1, len(rows) - 1):
        diff_val = float(rows[row_idx][7].text.replace("+", "").replace(".", "", 1).replace(",", ".").split("<")[0] or 0) if isinstance(rows[row_idx][7], Paragraph) else 0

    table.setStyle(TableStyle(style_cmds))

    return [
        Paragraph(f"<b>{group_name}</b> ({len(items99)} kalem #99 / {len(items101)} kalem #101)", s["groupTitle"]),
        table,
        Spacer(1, 5 * mm),
    ]


def _build_summary_table(items99, items101, total99, total101, s):
    cost99 = sum(float(i["unit_cost"] or 0) * i["quantity"] for i in items99)
    cost101 = sum(float(i["unit_cost"] or 0) * i["quantity"] for i in items101)
    items_count_99 = len(items99)
    items_count_101 = len(items101)
    total_qty_99 = sum(i["quantity"] for i in items99)
    total_qty_101 = sum(i["quantity"] for i in items101)
    weight99 = sum(float(i["weight_kg"] or 0) * i["quantity"] for i in items99)
    weight101 = sum(float(i["weight_kg"] or 0) * i["quantity"] for i in items101)
    area99 = sum(float(i["cut_area_m2"] or 0) * i["quantity"] for i in items99)
    area101 = sum(float(i["cut_area_m2"] or 0) * i["quantity"] for i in items101)

    header = [
        Paragraph("<b>OZET KIYASLAMA</b>", s["hdr"]),
        Paragraph("<b>Teklif #99</b>", s["hdr"]),
        Paragraph("<b>Teklif #101</b>", s["hdr"]),
        Paragraph("<b>Fark</b>", s["hdr"]),
    ]

    rows = [header]
    data = [
        ("Kalem Sayisi", str(items_count_99), str(items_count_101), str(items_count_101 - items_count_99)),
        ("Toplam Miktar", str(total_qty_99), str(total_qty_101), str(total_qty_101 - total_qty_99)),
        ("Toplam Agirlik (kg)", f"{weight99:.2f}", f"{weight101:.2f}", f"{weight101 - weight99:+.2f}"),
        ("Toplam Kesim Alani (m2)", f"{area99:.3f}", f"{area101:.3f}", f"{area101 - area99:+.3f}"),
        ("Maliyet Toplam", _fmt(cost99), _fmt(cost101), _fmt(cost101 - cost99)),
        ("Satis Toplam (KDV Hariç)", _fmt(total99), _fmt(total101), _fmt(total101 - total99)),
    ]

    for label, v99, v101, diff in data:
        rows.append([
            Paragraph(label, s["body"]),
            Paragraph(v99, s["right"]),
            Paragraph(v101, s["right"]),
            Paragraph(diff, s["right"]),
        ])

    rows.append([
        Paragraph("<b>GENEL TOPLAM</b>", s["grandLabel"]),
        Paragraph(f"<b>{_fmt(total99)}</b>", s["grandValue"]),
        Paragraph(f"<b>{_fmt(total101)}</b>", s["grandValue"]),
        Paragraph(f"<b>{_fmt(total101 - total99)}</b>", s["grandValue"]),
    ])

    table = Table(rows, colWidths=[60 * mm, 55 * mm, 55 * mm, 55 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#94a3b8")),
        ("LINEBELOW", (0, 0), (-1, 0), 1, TEAL),
        ("INNERGRID", (0, 1), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, ROW_ALT]),
        ("BACKGROUND", (0, -1), (-1, -1), TEAL_LIGHT),
        ("LINEABOVE", (0, -1), (-1, -1), 1.2, TEAL_DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))

    return [Spacer(1, 4 * mm), table]


def main():
    db_path = "data/whatsapp_bot.sqlite3"
    output_path = os.path.expanduser("~/Desktop/Teklif_Karsilastirma_99_vs_101.pdf")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM quote WHERE id = 99")
    q99 = dict(cursor.fetchone())
    cursor.execute("SELECT * FROM quote WHERE id = 101")
    q101 = dict(cursor.fetchone())

    cursor.execute("SELECT * FROM quote_item WHERE quote_id = 99 ORDER BY id")
    items99 = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM quote_item WHERE quote_id = 101 ORDER BY id")
    items101 = [dict(r) for r in cursor.fetchall()]

    conn.close()

    result = build_comparison_pdf(q99, items99, q101, items101, output_path)
    print(f"PDF olusturuldu: {result}")


if __name__ == "__main__":
    main()
