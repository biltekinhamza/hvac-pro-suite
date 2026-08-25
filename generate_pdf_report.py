#!/usr/bin/env python3
"""
Generate a single-page PDF report comparing quote #99 (old) vs #101 (new)
All parts converted to 0.80mm sheet metal
"""

import sys
sys.path.insert(0, r"C:\Users\TavSan\Desktop\HVAC Pro Suite")

from decimal import Decimal
from app.database import db
from app.utils import loads_json, q2
from fpdf import FPDF


class PDFReport(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(30, 60, 120)
        self.cell(0, 8, self._safe('HVAC Pro Suite - Teklif Karsilastirma Raporu'), 0, 1, 'C')
        self.set_font('Helvetica', '', 10)
        self.set_text_color(80, 80, 80)
        self.cell(0, 6, self._safe('Teklif #99 (Eski) vs Teklif #101 (Yeni - 0.80mm Sac)'), 0, 1, 'C')
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def _safe(self, text):
        """Replace Turkish chars for latin-1 encoding"""
        return (text
            .replace('ı', 'i').replace('İ', 'I')
            .replace('ğ', 'g').replace('Ğ', 'G')
            .replace('ü', 'u').replace('Ü', 'U')
            .replace('ş', 's').replace('Ş', 'S')
            .replace('ö', 'o').replace('Ö', 'O')
            .replace('ç', 'c').replace('Ç', 'C'))

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Sayfa {self.page_no()}/{{nb}}', 0, 0, 'C')

    def section_title(self, title):
        self.set_font('Helvetica', 'B', 11)
        self.set_fill_color(230, 235, 245)
        self.set_text_color(30, 60, 120)
        self.cell(0, 7, self._safe(title), 0, 1, 'L', fill=True)
        self.set_text_color(0)
        self.ln(1)

    def summary_row(self, label, old_val, new_val, diff_pct=None):
        self.set_font('Helvetica', '', 9)
        self.cell(65, 5, self._safe(label), 0, 0)
        self.set_font('Helvetica', '', 9)
        self.cell(40, 5, f'{old_val:>15s}', 0, 0, 'R')
        self.cell(40, 5, f'{new_val:>15s}', 0, 0, 'R')
        if diff_pct is not None:
            color = (0, 150, 0) if diff_pct > 0 else (200, 0, 0)
            self.set_text_color(*color)
            self.cell(35, 5, f'{diff_pct:+.1f}%', 0, 1, 'R')
            self.set_text_color(0)
        else:
            self.cell(35, 5, '', 0, 1)


def format_tl(val):
    return f'{val:,.2f} TL'.replace(',', 'X').replace('.', ',').replace('X', '.')


def main():
    # Fetch data from database
    with db.connect() as conn:
        quote99 = conn.execute("SELECT * FROM quote WHERE id = 99").fetchone()
        items99 = conn.execute("SELECT * FROM quote_item WHERE quote_id = 99 ORDER BY id").fetchall()
        quote101 = conn.execute("SELECT * FROM quote WHERE id = 101").fetchone()
        items101 = conn.execute("SELECT * FROM quote_item WHERE quote_id = 101 ORDER BY id").fetchall()

    # Build lookup for new items by part_code + izolasyon
    def make_key(item):
        inputs = loads_json(item["inputs_json"], {})
        iz = inputs.get("izolasyon_ozellik_id", "")
        return f"{item['part_code']}_{iz}"

    new_items_map = {make_key(item): item for item in items101}

    # Create PDF
    pdf = PDFReport('P', 'mm', 'A4')
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Summary section
    pdf.section_title('GENEL OZET')
    old_total = float(quote99["total_amount"])
    new_total = float(quote101["total_amount"])
    diff_total = new_total - old_total
    diff_pct = (diff_total / old_total) * 100

    pdf.summary_row('Musteri:', quote99["customer_name"], quote101["customer_name"])
    pdf.summary_row('Kar Orani:', f'%{quote99["profit_rate"]:.0f}', f'%{quote101["profit_rate"]:.0f}')
    pdf.summary_row('Durum:', quote99["status"], quote101["status"])
    pdf.ln(2)
    pdf.summary_row('Eski Toplam:', format_tl(old_total), format_tl(new_total), diff_pct)
    pdf.summary_row('Fark:', '', f'{format_tl(diff_total)}', diff_pct)
    pdf.ln(4)

    # Table header
    pdf.section_title('KALAT DETAY KARSILASTIRMA')
    
    col_w = [8, 28, 12, 18, 22, 22, 22, 18, 22, 18]
    headers = ['#', 'Parca', 'Adet', 'Eski Maliyet', 'Yeni Maliyet', 'Fark', 'Eski Fiyat', 'Yeni Fiyat', 'Fark', 'Satir Top.']
    
    pdf.set_font('Helvetica', 'B', 7)
    pdf.set_fill_color(30, 60, 120)
    pdf.set_text_color(255)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 6, h, 1, 0, 'C', fill=True)
    pdf.ln()
    pdf.set_text_color(0)

    # Table rows
    pdf.set_font('Helvetica', '', 6.5)
    row_num = 0
    for item99 in items99:
        row_num += 1
        key = make_key(item99)
        item101 = new_items_map.get(key)
        
        if not item101:
            continue
        
        old_cost = float(item99["unit_cost"])
        new_cost = float(item101["unit_cost"])
        old_price = float(item99["unit_price"])
        new_price = float(item101["unit_price"])
        old_line = float(item99["line_total"])
        new_line = float(item101["line_total"])
        
        cost_diff = new_cost - old_cost
        price_diff = new_price - old_price
        cost_pct = (cost_diff / old_cost * 100) if old_cost else 0
        price_pct = (price_diff / old_price * 100) if old_price else 0
        
        inputs = loads_json(item99["inputs_json"], {})
        iz = inputs.get("izolasyon_ozellik_id", "")
        iz_label = " (Izo)" if iz else ""
        part_name = pdf._safe(f"{item99['part_name']}{iz_label}")
        
        # Alternate row colors
        if row_num % 2 == 0:
            pdf.set_fill_color(245, 248, 255)
        else:
            pdf.set_fill_color(255, 255, 255)
        
        pdf.cell(col_w[0], 5, str(row_num), 1, 0, 'C', fill=True)
        pdf.cell(col_w[1], 5, part_name[:25], 1, 0, 'L', fill=True)
        pdf.cell(col_w[2], 5, str(item99["quantity"]), 1, 0, 'C', fill=True)
        pdf.cell(col_w[3], 5, format_tl(old_cost), 1, 0, 'R', fill=True)
        pdf.cell(col_w[4], 5, format_tl(new_cost), 1, 0, 'R', fill=True)
        pdf.cell(col_w[5], 5, f'{cost_pct:+.0f}%', 1, 0, 'R', fill=True)
        pdf.cell(col_w[6], 5, format_tl(old_price), 1, 0, 'R', fill=True)
        pdf.cell(col_w[7], 5, format_tl(new_price), 1, 0, 'R', fill=True)
        pdf.cell(col_w[8], 5, f'{price_pct:+.0f}%', 1, 0, 'R', fill=True)
        pdf.cell(col_w[9], 5, format_tl(new_line), 1, 1, 'R', fill=True)

    # Totals row
    pdf.set_font('Helvetica', 'B', 7)
    pdf.set_fill_color(220, 230, 245)
    pdf.cell(sum(col_w[:3]), 6, 'TOPLAM', 1, 0, 'R', fill=True)
    pdf.cell(col_w[3], 6, '', 1, 0, 'R', fill=True)
    pdf.cell(col_w[4], 6, '', 1, 0, 'R', fill=True)
    pdf.cell(col_w[5], 6, '', 1, 0, 'R', fill=True)
    pdf.cell(col_w[6], 6, '', 1, 0, 'R', fill=True)
    pdf.cell(col_w[7], 6, '', 1, 0, 'R', fill=True)
    pdf.cell(col_w[8], 6, '', 1, 0, 'R', fill=True)
    pdf.cell(col_w[9], 6, format_tl(new_total), 1, 1, 'R', fill=True)

    pdf.ln(4)

    # Notes
    pdf.section_title('NOTLAR')
    pdf.set_font('Helvetica', '', 8)
    notes = [
        '1. Tum parcalar 0.80mm sac kalinligina gore yeniden hesaplanmistir.',
        '2. Eski teklif #99: 0.50mm, 0.60mm, 0.80mm karisik kalinlik iceriyordu.',
        '3. Yuvarlak parcalar (dirsek, saplama) maliyeti ~%33 artmistir.',
        '4. Dikdortgen kanallar (ince sacli olanlar) maliyeti %26-46 artmistir.',
        '5. Zaten 0.80mm olan parcalar (kutu, kare dirsek, reduksiyon) degismemistir.',
        '6. Izolasyonlu kalemlerde izolasyon maliyeti korunmustur, sadece sac maliyeti guncellenmistir.',
        '7. Yeni teklif #101 "review" (taslak) durumundadir, Parasut\'e gonderilmemistir.',
    ]
    for note in notes:
        pdf.cell(0, 4.5, pdf._safe(note), 0, 1)

    # Save
    output_path = r"C:\Users\TavSan\Desktop\Teklif_99_vs_101_Karsilastirma.pdf"
    pdf.output(output_path)
    print(f"PDF olusturuldu: {output_path}")


if __name__ == "__main__":
    main()