from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from html import escape
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.config import Settings

FONT_PATHS = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
)

TEAL_DARK = colors.HexColor("#134e4a")
TEAL = colors.HexColor("#0f766e")
TEAL_LIGHT = colors.HexColor("#ccfbf1")
SLATE = colors.HexColor("#1e293b")
SLATE_MUTED = colors.HexColor("#64748b")
BORDER = colors.HexColor("#cbd5e1")
ROW_ALT = colors.HexColor("#f8fafc")


def build_quote_pdf(payload: dict, settings: Settings) -> bytes:
    font_name = _register_font()
    quote = payload["quote"]
    items = payload["items"]
    vat_rate = int(settings.default_vat_rate or 0)

    items_subtotal = sum((_decimal(item["line_total"]) for item in items), _decimal(0))
    shipping = _decimal(quote.get("shipping_amount"))
    ara_toplam = items_subtotal + shipping
    kdv = (ara_toplam * _decimal(vat_rate) / _decimal(100)).quantize(
        _decimal("0.01"), rounding=ROUND_HALF_UP
    )
    genel_toplam = ara_toplam + kdv

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=20 * mm,
        bottomMargin=22 * mm,
        title=f"Teklif #{quote['id']}",
        author=settings.app_name,
    )
    story = _story(quote, items, settings, font_name, vat_rate, ara_toplam, shipping, kdv, genel_toplam)

    footer = _FooterFactory(settings, font_name)
    document.build(story, onFirstPage=footer.canvas_factory, onLaterPages=footer.canvas_factory)
    return buffer.getvalue()


def _story(quote, items, settings, font_name, vat_rate, ara_toplam, shipping, kdv, genel_toplam):
    s = _styles(font_name)
    return (
        _header(quote, settings, s)
        + _items_table(items, s)
        + _totals(ara_toplam, shipping, kdv, genel_toplam, vat_rate, s)
    )


def _styles(font_name: str) -> dict:
    base = getSampleStyleSheet()
    return {
        "company": ParagraphStyle(
            "Company", parent=base["Title"], fontName=font_name, fontSize=20, leading=24,
            textColor=TEAL_DARK,
        ),
        "docTitle": ParagraphStyle(
            "DocTitle", parent=base["Title"], fontName=font_name, fontSize=15, leading=18,
            textColor=TEAL_DARK, alignment=TA_RIGHT,
        ),
        "muted": ParagraphStyle(
            "Muted", parent=base["BodyText"], fontName=font_name, fontSize=8, leading=11,
            textColor=SLATE_MUTED,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontName=font_name, fontSize=9, leading=13,
            textColor=SLATE,
        ),
        "right": ParagraphStyle(
            "Right", parent=base["BodyText"], fontName=font_name, fontSize=9, leading=13,
            textColor=SLATE, alignment=TA_RIGHT,
        ),
        "hdr": ParagraphStyle(
            "Hdr", parent=base["BodyText"], fontName=font_name, fontSize=8, leading=11,
            textColor=colors.white,
        ),
        "metaLabel": ParagraphStyle(
            "MetaLabel", parent=base["BodyText"], fontName=font_name, fontSize=8, leading=12,
            textColor=SLATE_MUTED,
        ),
        "metaValue": ParagraphStyle(
            "MetaValue", parent=base["BodyText"], fontName=font_name, fontSize=9, leading=12,
            textColor=SLATE,
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
            "GrandValue", parent=base["BodyText"], fontName=font_name, fontSize=11, leading=14,
            textColor=TEAL_DARK, alignment=TA_RIGHT,
        ),
    }


def _header(quote, settings, s) -> list:
    name = escape(str(settings.company_name or settings.app_name))
    parts = [part for part in [settings.company_address, settings.company_phone] if part]
    contact = escape(" • ".join(parts)) if parts else ""

    left = Table(
        [[Paragraph(f"<b>{name}</b>", s["company"])]]
        + ([[""]] if not contact else [[Paragraph(contact, s["muted"])]]),
        colWidths=[105 * mm],
    )
    left.setStyle(_cell_padding(0, 1))
    right = Table([[Paragraph("<b>TEKLİF</b>", s["docTitle"])]], colWidths=[55 * mm])
    right.setStyle(_cell_padding(0, 1))

    head = Table([[left, right]], colWidths=[105 * mm, 55 * mm])
    head.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    meta = Table(
        [
            [Paragraph("Teklif No", s["metaLabel"]), Paragraph(f"#{quote['id']}", s["metaValue"])],
            [Paragraph("Müşteri", s["metaLabel"]), Paragraph(escape(str(quote["customer_name"])), s["metaValue"])],
            [Paragraph("Tarih", s["metaLabel"]), Paragraph(_format_date(quote.get("created_at")), s["metaValue"])],
        ],
        colWidths=[28 * mm, 78 * mm],
    )
    meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ROW_ALT),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))

    return [head, Spacer(1, 6 * mm), meta, Spacer(1, 7 * mm)]


def _items_table(items, s) -> list:
    rows = [
        [
            Paragraph("Ürün / Açıklama", s["hdr"]),
            Paragraph("Miktar", s["hdr"]),
            Paragraph("Birim Fiyat", s["hdr"]),
            Paragraph("Tutar", s["hdr"]),
        ]
    ]
    for item in items:
        detail = "<br/>".join(escape(str(part)) for part in item.get("detail_parts", [])[1:])
        description = f"<b>{escape(str(item.get('display_name') or item['part_name']))}</b>"
        if detail:
            description += f"<br/><font size='7' color='#64748b'>{detail}</font>"
        rows.append([
            Paragraph(description, s["body"]),
            Paragraph(f"{escape(str(item.get('sales_quantity_text', item['quantity'])))} {escape(str(item.get('sales_unit_label', 'adet')))}", s["right"]),
            Paragraph(_format_money(item.get("sales_unit_price", item["unit_price"])), s["right"]),
            Paragraph(_format_money(item["line_total"]), s["right"]),
        ])
    table = Table(rows, repeatRows=1, colWidths=[91 * mm, 18 * mm, 26 * mm, 26 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL_DARK),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#94a3b8")),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, TEAL),
        ("INNERGRID", (0, 1), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
    ]))
    return [table, Spacer(1, 6 * mm)]


def _totals(ara_toplam, shipping, kdv, genel_toplam, vat_rate, s) -> list:
    rows = [
        [Paragraph("Nakliye", s["totLabel"]), Paragraph(_format_money(shipping), s["totValue"])],
        [Paragraph("Ara Toplam (KDV Hariç)", s["totLabel"]), Paragraph(_format_money(ara_toplam), s["totValue"])],
        [Paragraph(f"KDV (%{vat_rate})", s["totLabel"]), Paragraph(_format_money(kdv), s["totValue"])],
        [Paragraph("<b>Genel Toplam (KDV Dahil)</b>", s["grandLabel"]),
         Paragraph(f"<b>{_format_money(genel_toplam)}</b>", s["grandValue"])],
    ]
    table = Table(rows, colWidths=[58 * mm, 58 * mm], hAlign="RIGHT")
    table.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.HexColor("#e2e8f0")),
        ("LINEABOVE", (0, 3), (-1, 3), 1.2, TEAL_DARK),
        ("BACKGROUND", (0, 3), (-1, 3), TEAL_LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return [table]


def _cell_padding(top: float, bottom: float) -> TableStyle:
    return TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), top),
        ("BOTTOMPADDING", (0, 0), (-1, -1), bottom),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ])


class _FooterFactory:
    def __init__(self, settings: Settings, font_name: str) -> None:
        self.settings = settings
        self.font_name = font_name

    def canvas_factory(self, *args, **kwargs):
        return _FooterCanvas(*args, settings=self.settings, font_name=self.font_name, **kwargs)


class _FooterCanvas(canvas.Canvas):
    _saved = None

    def __init__(self, *args, settings=None, font_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._settings = settings
        self._font_name = font_name

    def showPage(self):
        self._draw_footer()
        super().showPage()

    def save(self):
        self._draw_footer()
        super().save()

    def _draw_footer(self):
        width, height = A4
        y = 12 * mm
        self.saveState()
        self.setStrokeColor(BORDER)
        self.setLineWidth(0.4)
        self.line(16 * mm, y + 6 * mm, width - 16 * mm, y + 6 * mm)
        self.setFillColor(SLATE_MUTED)
        self.setFont(self._font_name, 7.5)
        self.drawString(16 * mm, y, f"{self._settings.app_name} · Fiyatlar KDV hariçtir.")
        self.drawRightString(width - 16 * mm, y, f"Sayfa {self._pageNumber}")
        self.restoreState()


def _register_font() -> str:
    for path in FONT_PATHS:
        if path.is_file():
            font_name = "QuoteUnicode"
            if font_name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(font_name, str(path)))
            return font_name
    return "Helvetica"


def _decimal(value: object) -> Decimal:
    return Decimal(str(value or 0))


def _format_money(value: object) -> str:
    amount = f"{float(value or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{amount} TL"


def _format_date(value: object) -> str:
    text = str(value or "").strip()
    if len(text) >= 10 and text[4:5] == "-":
        return f"{text[8:10]}.{text[5:7]}.{text[:4]}"
    return text or "-"
