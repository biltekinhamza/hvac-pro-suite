from __future__ import annotations

import sqlite3
import secrets
from pathlib import Path
from typing import Any

from app.config import BASE_DIR
from app.database import db
from app.utils import D, dumps_json, loads_json, q2


class Repository:
    CSV_COLUMN_MAP = {
        "SPIRO BORU (Metre)": "spiro_boru",
        "90 DİRSEK": "yuvarlak_dirsek_90",
        "45 DİRSEK": "yuvarlak_dirsek_45",
        "T": "yuvarlak_te",
        "REDÜKSİYON": "yuvarlak_reduksiyon",
        "MANŞON": "yuvarlak_mason",
        "KELEPÇE": "yuvarlak_kelepce",
        "KLAPE": "yuvarlak_klape",
        "JETKAP": "yuvarlak_jetkap",
        "KÖRTAPA": "kortapa",
        "SAPLAMA": "yuvarlak_saplama",
        "ŞAPKA": "yuvarlak_sapka",
    }

    def get_round_part_price(self, part_code: str, cap_mm: int) -> float | None:
        with db.connect() as conn:
            row = conn.execute(
                "SELECT price FROM round_part_price WHERE part_code = ? AND cap_mm = ?",
                (part_code, cap_mm),
            ).fetchone()
            return float(row["price"]) if row else None

    def update_round_part_price(self, part_code: str, cap_mm: int, price: float) -> None:
        with db.tx() as conn:
            conn.execute("UPDATE round_part_price SET price = ? WHERE part_code = ? AND cap_mm = ?", (str(price), part_code, cap_mm))

    def upsert_round_part_price(self, part_code: str, cap_mm: int, price: float) -> None:
        with db.tx() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO round_part_price(part_code, cap_mm, price) VALUES(?, ?, ?)",
                (part_code, cap_mm, str(price)),
            )

    def load_round_prices_from_csv(self, csv_path: str) -> int:
        import csv
        count = 0
        with db.tx() as conn:
            conn.execute("DELETE FROM round_part_price")
            with open(csv_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    try:
                        cap_mm = int(row["ÇAP"].strip())
                    except (ValueError, KeyError):
                        continue
                    for col, part_code in self.CSV_COLUMN_MAP.items():
                        raw = row.get(col, "").strip().replace(",", ".")
                        if not raw:
                            continue
                        try:
                            price = float(raw)
                        except ValueError:
                            continue
                        conn.execute(
                            "INSERT INTO round_part_price(part_code, cap_mm, price) VALUES(?, ?, ?)",
                            (part_code, cap_mm, str(price)),
                        )
                        count += 1
            conn.commit()
        return count

    def seed_round_prices_if_empty(self) -> None:
        with db.connect() as conn:
            count = conn.execute("SELECT COUNT(*) AS c FROM round_part_price").fetchone()["c"]
            if count:
                return
        csv_path = str(BASE_DIR / "data" / "yuvarlak_fiyatlari.csv")
        if Path(csv_path).exists():
            self.load_round_prices_from_csv(csv_path)

    def seed_from_desktop_if_empty(self) -> None:
        source = BASE_DIR.parent / "Havalandirma" / "data" / "havalandirma.sqlite3"
        with db.tx() as conn:
            count = conn.execute("SELECT COUNT(*) AS c FROM material_option").fetchone()["c"]
            if count or not source.exists():
                return

            src = sqlite3.connect(source)
            src.row_factory = sqlite3.Row
            try:
                materials = src.execute("SELECT * FROM material ORDER BY id").fetchall()
                for row in materials:
                    conn.execute("INSERT INTO material(id, name, unit) VALUES(?, ?, ?)", (row["id"], row["name"], row["unit"]))
                options = src.execute("SELECT * FROM material_option ORDER BY id").fetchall()
                for row in options:
                    conn.execute(
                        "INSERT INTO material_option(id, material_id, option_name, quantity, average_unit_cost) VALUES(?, ?, ?, ?, ?)",
                        (row["id"], row["material_id"], row["option_name"], row["quantity"], row["average_unit_cost"]),
                    )
            finally:
                src.close()

    def get_material_option(self, option_id: int) -> sqlite3.Row:
        with db.connect() as conn:
            row = conn.execute(
                """
                SELECT mo.id, mo.option_name, mo.quantity, mo.average_unit_cost, mo.is_available, m.name, m.unit
                FROM material_option mo
                JOIN material m ON m.id = mo.material_id
                WHERE mo.id = ?
                """,
                (option_id,),
            ).fetchone()
            if not row:
                raise ValueError("Malzeme özelliği bulunamadı.")
            return row

    def find_options_by_name(self, keyword: str) -> list[sqlite3.Row]:
        with db.connect() as conn:
            return conn.execute(
                """
                SELECT mo.id, m.name, mo.option_name, mo.quantity, mo.average_unit_cost, m.unit
                FROM material_option mo
                JOIN material m ON m.id = mo.material_id
                WHERE UPPER(m.name) LIKE ?
                ORDER BY mo.id
                """,
                (f"%{keyword.upper()}%",),
            ).fetchall()

    def find_available_options_by_name(self, keyword: str) -> list[sqlite3.Row]:
        with db.connect() as conn:
            return conn.execute(
                """
                SELECT mo.id, m.name, mo.option_name, mo.quantity, mo.average_unit_cost, mo.is_available, m.unit
                FROM material_option mo
                JOIN material m ON m.id = mo.material_id
                WHERE UPPER(m.name) LIKE ? AND mo.is_available = 1
                ORDER BY mo.option_name
                """,
                (f"%{keyword.upper()}%",),
            ).fetchall()

    def find_first_option_by_name(self, keyword: str) -> sqlite3.Row | None:
        with db.connect() as conn:
            return conn.execute(
                """
                SELECT mo.id, m.name, mo.option_name, mo.quantity, mo.average_unit_cost, m.unit
                FROM material_option mo
                JOIN material m ON m.id = mo.material_id
                WHERE UPPER(m.name) LIKE ?
                ORDER BY mo.id
                LIMIT 1
                """,
                (f"%{keyword.upper()}%",),
            ).fetchone()

    def find_option_by_name_and_option(self, name_keyword: str, option_keyword: str) -> sqlite3.Row | None:
        with db.connect() as conn:
            return conn.execute(
                """
                SELECT mo.id, m.name, mo.option_name, mo.quantity, mo.average_unit_cost, m.unit
                FROM material_option mo
                JOIN material m ON m.id = mo.material_id
                WHERE UPPER(m.name) LIKE ? AND UPPER(mo.option_name) LIKE ?
                ORDER BY mo.id
                LIMIT 1
                """,
                (f"%{name_keyword.upper()}%", f"%{option_keyword.upper()}%"),
            ).fetchone()

    def find_square_sheet_option(self, thickness: object) -> sqlite3.Row | None:
        target = D(thickness)
        if target <= 0:
            return self.find_first_option_by_name("SAC")
        rows = [*self.find_options_by_name("KARE KANAL SAC"), *self.find_options_by_name("SAC")]
        seen: set[int] = set()
        for row in rows:
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            raw = str(row["option_name"] or "").strip().split()[0]
            try:
                if D(raw) == target:
                    return row
            except Exception:
                continue
        return None

    def list_material_options(self) -> list[sqlite3.Row]:
        with db.connect() as conn:
            return conn.execute(
                """
                SELECT mo.id, m.name, mo.option_name, m.unit, mo.quantity, mo.average_unit_cost, mo.is_available
                FROM material_option mo
                JOIN material m ON m.id = mo.material_id
                ORDER BY m.name, mo.option_name
                """
            ).fetchall()

    def list_materials(self) -> list[sqlite3.Row]:
        with db.connect() as conn:
            return conn.execute("SELECT id, name, unit FROM material ORDER BY name").fetchall()

    def add_material_option(self, material_name: str, option_name: str, average_unit_cost: float) -> sqlite3.Row:
        with db.tx() as conn:
            material = conn.execute("SELECT id FROM material WHERE name = ?", (material_name.upper(),)).fetchone()
            if not material:
                conn.execute("INSERT INTO material(name, unit) VALUES (?, 'm2')", (material_name.upper(),))
                conn.commit()
                material = conn.execute("SELECT id FROM material WHERE name = ?", (material_name.upper(),)).fetchone()
            conn.execute(
                "INSERT INTO material_option(material_id, option_name, quantity, average_unit_cost) VALUES (?, ?, 1000, ?)",
                (material["id"], option_name, str(q2(average_unit_cost))),
            )
            return conn.execute(
                """
                SELECT mo.id, m.name, mo.option_name, m.unit, mo.quantity, mo.average_unit_cost, mo.is_available
                FROM material_option mo
                JOIN material m ON m.id = mo.material_id
                WHERE mo.id = last_insert_rowid()
                """
            ).fetchone()

    def update_material_option_cost(self, option_id: int, average_unit_cost: Any) -> sqlite3.Row:
        with db.tx() as conn:
            row = conn.execute("SELECT id FROM material_option WHERE id = ?", (option_id,)).fetchone()
            if not row:
                raise ValueError("Malzeme ozelligi bulunamadi.")
            conn.execute(
                "UPDATE material_option SET average_unit_cost = ? WHERE id = ?",
                (str(q2(average_unit_cost)), option_id),
            )
            return conn.execute(
                """
                SELECT mo.id, m.name, mo.option_name, m.unit, mo.quantity, mo.average_unit_cost, mo.is_available
                FROM material_option mo
                JOIN material m ON m.id = mo.material_id
                WHERE mo.id = ?
                """,
                (option_id,),
            ).fetchone()

    def update_material_option_availability(self, option_id: int, is_available: bool) -> sqlite3.Row:
        with db.tx() as conn:
            row = conn.execute("SELECT id FROM material_option WHERE id = ?", (option_id,)).fetchone()
            if not row:
                raise ValueError("Malzeme özelliği bulunamadı.")
            conn.execute("UPDATE material_option SET is_available = ? WHERE id = ?", (int(is_available), option_id))
            return conn.execute(
                """
                SELECT mo.id, m.name, mo.option_name, m.unit, mo.quantity, mo.average_unit_cost, mo.is_available
                FROM material_option mo
                JOIN material m ON m.id = mo.material_id
                WHERE mo.id = ?
                """,
                (option_id,),
            ).fetchone()

    def delete_material_option(self, option_id: int) -> None:
        with db.tx() as conn:
            row = conn.execute("SELECT id FROM material_option WHERE id = ?", (option_id,)).fetchone()
            if not row:
                raise ValueError("Malzeme ozelligi bulunamadi.")
            conn.execute("DELETE FROM material_option WHERE id = ?", (option_id,))

    def get_active_cart(self, cart_token: str, session_id: int | None = None) -> sqlite3.Row:
        with db.tx() as conn:
            row = conn.execute("SELECT * FROM cart WHERE status = 'active' AND cart_token = ?", (cart_token,)).fetchone()
            if row:
                return row
            conn.execute(
                "INSERT INTO cart(session_id, cart_token, status, customer_name, shipping_amount) VALUES(?, ?, 'active', '', 0)",
                (session_id, cart_token),
            )
            return conn.execute("SELECT * FROM cart WHERE cart_token = ? AND status = 'active'", (cart_token,)).fetchone()

    def get_customer_session_by_token(self, token: str) -> sqlite3.Row | None:
        with db.connect() as conn:
            return conn.execute("SELECT * FROM customer_session WHERE session_token = ? AND status = 'active'", (token,)).fetchone()

    def claim_legacy_cart(self, cart_id: int, cart_token: str) -> sqlite3.Row:
        with db.tx() as conn:
            cart = conn.execute(
                "SELECT * FROM cart WHERE id = ? AND status = 'active' AND cart_token IS NULL",
                (cart_id,),
            ).fetchone()
            if not cart:
                raise ValueError("Kurtarılabilir eski sepet bulunamadı.")
            conn.execute("UPDATE cart SET cart_token = ? WHERE id = ?", (cart_token, cart_id))
            return conn.execute("SELECT * FROM cart WHERE id = ?", (cart_id,)).fetchone()

    def get_or_create_customer_session(self, whatsapp_phone: str) -> sqlite3.Row:
        phone = whatsapp_phone.strip()
        with db.tx() as conn:
            row = conn.execute(
                "SELECT * FROM customer_session WHERE whatsapp_phone = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
                (phone,),
            ).fetchone()
            if row:
                return row
            token = secrets.token_urlsafe(18)
            conn.execute(
                "INSERT INTO customer_session(session_token, whatsapp_phone, status) VALUES(?, ?, 'active')",
                (token, phone),
            )
            return conn.execute("SELECT * FROM customer_session WHERE session_token = ?", (token,)).fetchone()

    def set_customer_session_contact(self, session_id: int, parasut_contact_id: str, customer_name: str) -> None:
        with db.tx() as conn:
            conn.execute(
                "UPDATE customer_session SET parasut_contact_id = ?, customer_name = ?, pending_action = NULL WHERE id = ?",
                (parasut_contact_id, customer_name, session_id),
            )

    def set_customer_session_pending_action(self, session_id: int, action: str | None) -> None:
        with db.tx() as conn:
            conn.execute("UPDATE customer_session SET pending_action = ? WHERE id = ?", (action, session_id))

    def add_cart_item(self, cart_token: str, part_code: str, inputs: dict[str, Any], quantity: int) -> int:
        cart = self.get_active_cart(cart_token)
        with db.tx() as conn:
            matching = [
                row for row in conn.execute(
                    "SELECT id, inputs_json, quantity FROM cart_item WHERE cart_id = ? AND part_code = ? ORDER BY id",
                    (cart["id"], part_code),
                ).fetchall()
                if loads_json(row["inputs_json"], {}) == inputs
            ]
            if matching:
                item_id = int(matching[0]["id"])
                total_quantity = quantity + sum(int(row["quantity"]) for row in matching)
                conn.execute("UPDATE cart_item SET quantity = ? WHERE id = ?", (total_quantity, item_id))
                if len(matching) > 1:
                    conn.executemany("DELETE FROM cart_item WHERE id = ?", [(row["id"],) for row in matching[1:]])
                return item_id
            cur = conn.execute(
                "INSERT INTO cart_item(cart_id, part_code, inputs_json, quantity) VALUES(?, ?, ?, ?)",
                (cart["id"], part_code, dumps_json(inputs), quantity),
            )
            return int(cur.lastrowid)

    def list_cart_items(self, cart_token: str) -> list[sqlite3.Row]:
        cart = self.get_active_cart(cart_token)
        with db.connect() as conn:
            return conn.execute("SELECT * FROM cart_item WHERE cart_id = ? ORDER BY id", (cart["id"],)).fetchall()

    def list_pending_carts(self) -> list[sqlite3.Row]:
        with db.connect() as conn:
            return conn.execute(
                """
                SELECT c.id, c.created_at, cs.customer_name, cs.whatsapp_phone, COUNT(ci.id) AS item_count
                FROM cart c
                JOIN cart_item ci ON ci.cart_id = c.id
                LEFT JOIN customer_session cs ON cs.id = c.session_id
                WHERE c.status = 'active'
                GROUP BY c.id, c.created_at, cs.customer_name, cs.whatsapp_phone
                ORDER BY c.created_at DESC, c.id DESC
                """
            ).fetchall()

    def list_cart_items_for_admin(self, cart_id: int) -> list[sqlite3.Row]:
        with db.connect() as conn:
            return conn.execute("SELECT * FROM cart_item WHERE cart_id = ? ORDER BY id", (cart_id,)).fetchall()

    def update_cart_item_for_admin(self, cart_id: int, item_id: int, inputs: dict[str, Any], quantity: int) -> None:
        with db.tx() as conn:
            row = conn.execute(
                "SELECT ci.id FROM cart_item ci JOIN cart c ON c.id = ci.cart_id WHERE ci.id = ? AND c.id = ? AND c.status = 'active'",
                (item_id, cart_id),
            ).fetchone()
            if not row:
                raise ValueError("Sepet kalemi bulunamadı.")
            conn.execute("UPDATE cart_item SET inputs_json = ?, quantity = ? WHERE id = ?", (dumps_json(inputs), quantity, item_id))

    def delete_cart_item_for_admin(self, cart_id: int, item_id: int) -> None:
        with db.tx() as conn:
            row = conn.execute(
                "SELECT ci.id FROM cart_item ci JOIN cart c ON c.id = ci.cart_id WHERE ci.id = ? AND c.id = ? AND c.status = 'active'",
                (item_id, cart_id),
            ).fetchone()
            if not row:
                raise ValueError("Sepet kalemi bulunamadı.")
            conn.execute("DELETE FROM cart_item WHERE id = ?", (item_id,))

    def cancel_pending_cart(self, cart_id: int) -> None:
        with db.tx() as conn:
            row = conn.execute("SELECT id FROM cart WHERE id = ? AND status = 'active'", (cart_id,)).fetchone()
            if not row:
                raise ValueError("Bekleyen sepet bulunamadı.")
            conn.execute("UPDATE cart SET status = 'cancelled' WHERE id = ?", (cart_id,))

    def update_cart_item_quantity(self, cart_token: str, item_id: int, quantity: int, inputs: dict[str, Any] | None = None) -> None:
        cart = self.get_active_cart(cart_token)
        with db.tx() as conn:
            row = conn.execute("SELECT id FROM cart_item WHERE id = ? AND cart_id = ?", (item_id, cart["id"])).fetchone()
            if not row:
                raise ValueError("Kalem bulunamadi.")
            if inputs is None:
                conn.execute("UPDATE cart_item SET quantity = ? WHERE id = ?", (quantity, item_id))
            else:
                conn.execute("UPDATE cart_item SET inputs_json = ?, quantity = ? WHERE id = ?", (dumps_json(inputs), quantity, item_id))

    def delete_cart_item(self, cart_token: str, item_id: int) -> None:
        cart = self.get_active_cart(cart_token)
        with db.tx() as conn:
            row = conn.execute("SELECT id FROM cart_item WHERE id = ? AND cart_id = ?", (item_id, cart["id"])).fetchone()
            if not row:
                raise ValueError("Kalem bulunamadi.")
            conn.execute("DELETE FROM cart_item WHERE id = ?", (item_id,))

    def create_quote(self, cart_token: str, customer_name: str, shipping_amount: Any, items: list[dict[str, Any]]) -> int:
        cart = self.get_active_cart(cart_token)
        with db.tx() as conn:
            cur = conn.execute(
                "INSERT INTO quote(cart_id, customer_name, profit_rate, shipping_amount, total_amount, status) VALUES(?, ?, 0, ?, 0, 'review')",
                (cart["id"], customer_name.strip() or "Genel Müşteri", str(q2(shipping_amount))),
            )
            quote_id = int(cur.lastrowid)
            total = q2(shipping_amount)
            for item in items:
                conn.execute(
                    """
                    INSERT INTO quote_item(
                        quote_id, part_code, part_name, quantity, unit_cost, unit_price, line_total,
                        cut_area_m2, weight_kg, inputs_json, result_json
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        quote_id,
                        item["part_code"],
                        item["part_name"],
                        item["quantity"],
                        str(q2(item["unit_cost"])),
                        str(q2(item["unit_price"])),
                        str(q2(item["line_total"])),
                        str(item["cut_area_m2"]),
                        str(item["weight_kg"]),
                        dumps_json(item["inputs"]),
                        dumps_json(item["result"]),
                    ),
                )
                total += D(item["line_total"])
            conn.execute("UPDATE quote SET total_amount = ? WHERE id = ?", (str(q2(total)), quote_id))
            conn.execute("UPDATE cart SET status='converted', cart_token = NULL WHERE id = ?", (cart["id"],))
            conn.execute(
                "INSERT INTO cart(session_id, cart_token, status, customer_name, shipping_amount) VALUES(?, ?, 'active', '', 0)",
                (cart["session_id"], cart_token),
            )
            return quote_id

    def create_quote_for_admin(self, cart_id: int, customer_name: str, shipping_amount: Any, items: list[dict[str, Any]]) -> int:
        with db.tx() as conn:
            cart = conn.execute("SELECT * FROM cart WHERE id = ? AND status = 'active'", (cart_id,)).fetchone()
            if not cart:
                raise ValueError("Bekleyen sepet bulunamadı.")
            cur = conn.execute(
                "INSERT INTO quote(cart_id, customer_name, profit_rate, shipping_amount, total_amount, status) VALUES(?, ?, 0, ?, 0, 'review')",
                (cart["id"], customer_name.strip() or "Genel Müşteri", str(q2(shipping_amount))),
            )
            quote_id = int(cur.lastrowid)
            total = q2(shipping_amount)
            for item in items:
                conn.execute(
                    """
                    INSERT INTO quote_item(
                        quote_id, part_code, part_name, quantity, unit_cost, unit_price, line_total,
                        cut_area_m2, weight_kg, inputs_json, result_json
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (quote_id, item["part_code"], item["part_name"], item["quantity"], str(q2(item["unit_cost"])), str(q2(item["unit_price"])), str(q2(item["line_total"])), str(item["cut_area_m2"]), str(item["weight_kg"]), dumps_json(item["inputs"]), dumps_json(item["result"])),
                )
                total += D(item["line_total"])
            conn.execute("UPDATE quote SET total_amount = ? WHERE id = ?", (str(q2(total)), quote_id))
            conn.execute("UPDATE cart SET status = 'converted', cart_token = NULL WHERE id = ?", (cart["id"],))
            return quote_id

    def add_quote_item(self, quote_id: int, item: dict[str, Any]) -> None:
        with db.tx() as conn:
            quote = conn.execute("SELECT id FROM quote WHERE id = ?", (quote_id,)).fetchone()
            if not quote:
                raise ValueError("Teklif bulunamadı.")
            conn.execute(
                """
                INSERT INTO quote_item(
                    quote_id, part_code, part_name, quantity, unit_cost, unit_price, line_total,
                    cut_area_m2, weight_kg, inputs_json, result_json
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    quote_id,
                    item["part_code"],
                    item["part_name"],
                    item["quantity"],
                    str(q2(item["unit_cost"])),
                    str(q2(item["unit_price"])),
                    str(q2(item["line_total"])),
                    str(item["cut_area_m2"]),
                    str(item["weight_kg"]),
                    dumps_json(item["inputs"]),
                    dumps_json(item["result"]),
                ),
            )
            self._refresh_quote_total(conn, quote_id)

    def update_quote_item(self, quote_id: int, item_id: int, item: dict[str, Any]) -> None:
        with db.tx() as conn:
            row = conn.execute("SELECT id FROM quote_item WHERE id = ? AND quote_id = ?", (item_id, quote_id)).fetchone()
            if not row:
                raise ValueError("Teklif kalemi bulunamadı.")
            conn.execute(
                """
                UPDATE quote_item
                SET part_code = ?, part_name = ?, quantity = ?, unit_cost = ?, unit_price = ?, line_total = ?,
                    cut_area_m2 = ?, weight_kg = ?, inputs_json = ?, result_json = ?
                WHERE id = ? AND quote_id = ?
                """,
                (
                    item["part_code"],
                    item["part_name"],
                    item["quantity"],
                    str(q2(item["unit_cost"])),
                    str(q2(item["unit_price"])),
                    str(q2(item["line_total"])),
                    str(item["cut_area_m2"]),
                    str(item["weight_kg"]),
                    dumps_json(item["inputs"]),
                    dumps_json(item["result"]),
                    item_id,
                    quote_id,
                ),
            )
            self._refresh_quote_total(conn, quote_id)

    def delete_quote_item(self, quote_id: int, item_id: int) -> None:
        with db.tx() as conn:
            row = conn.execute("SELECT id FROM quote_item WHERE id = ? AND quote_id = ?", (item_id, quote_id)).fetchone()
            if not row:
                raise ValueError("Teklif kalemi bulunamadı.")
            conn.execute("DELETE FROM quote_item WHERE id = ? AND quote_id = ?", (item_id, quote_id))
            self._refresh_quote_total(conn, quote_id)

    def _refresh_quote_total(self, conn: sqlite3.Connection, quote_id: int) -> None:
        quote = conn.execute("SELECT shipping_amount FROM quote WHERE id = ?", (quote_id,)).fetchone()
        if not quote:
            raise ValueError("Teklif bulunamadı.")
        item_total = conn.execute("SELECT COALESCE(SUM(line_total), 0) AS total FROM quote_item WHERE quote_id = ?", (quote_id,)).fetchone()["total"]
        total = D(item_total) + D(quote["shipping_amount"])
        conn.execute(
            "UPDATE quote SET total_amount = ?, parasut_offer_id = NULL, status = 'review' WHERE id = ?",
            (str(q2(total)), quote_id),
        )

    def create_quote_from_items(self, customer_name: str, profit_rate: Any, shipping_amount: Any, items: list[dict[str, Any]]) -> int:
        with db.tx() as conn:
            cur = conn.execute(
                "INSERT INTO quote(cart_id, customer_name, profit_rate, shipping_amount, total_amount, status) VALUES(NULL, ?, ?, ?, 0, 'review')",
                (customer_name.strip() or "Birleşik Teklif", str(q2(profit_rate)), str(q2(shipping_amount))),
            )
            quote_id = int(cur.lastrowid)
            for item in items:
                conn.execute(
                    """
                    INSERT INTO quote_item(
                        quote_id, part_code, part_name, quantity, unit_cost, unit_price, line_total,
                        cut_area_m2, weight_kg, inputs_json, result_json
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        quote_id,
                        item["part_code"],
                        item["part_name"],
                        item["quantity"],
                        str(q2(item["unit_cost"])),
                        str(q2(item["unit_price"])),
                        str(q2(item["line_total"])),
                        str(item["cut_area_m2"]),
                        str(item["weight_kg"]),
                        dumps_json(item["inputs"]),
                        dumps_json(item["result"]),
                    ),
                )
            self._refresh_quote_total(conn, quote_id)
            return quote_id

    def mark_quotes_merged(self, quote_ids: list[int]) -> None:
        if not quote_ids:
            return
        placeholders = ",".join("?" for _ in quote_ids)
        with db.tx() as conn:
            conn.execute(
                f"UPDATE quote SET status = 'merged' WHERE id IN ({placeholders})",
                tuple(quote_ids),
            )

    def delete_quotes(self, quote_ids: list[int]) -> int:
        if not quote_ids:
            return 0
        placeholders = ",".join("?" for _ in quote_ids)
        with db.tx() as conn:
            rows = conn.execute(f"SELECT id FROM quote WHERE id IN ({placeholders})", tuple(quote_ids)).fetchall()
            if len(rows) != len(set(quote_ids)):
                raise ValueError("Seçilen tekliflerden biri bulunamadı.")
            conn.execute(f"DELETE FROM quote WHERE id IN ({placeholders})", tuple(quote_ids))
            return len(rows)

    def apply_quote_profit_rate(self, quote_id: int, profit_rate: Any) -> None:
        rate = D(profit_rate)
        with db.tx() as conn:
            quote = conn.execute("SELECT id, shipping_amount FROM quote WHERE id = ?", (quote_id,)).fetchone()
            if not quote:
                raise ValueError("Teklif bulunamadı.")
            rows = conn.execute("SELECT id, unit_cost, quantity FROM quote_item WHERE quote_id = ?", (quote_id,)).fetchall()
            total = D(quote["shipping_amount"])
            for row in rows:
                unit_price = q2(D(row["unit_cost"]) * (D("1") + (rate / D("100"))))
                line_total = q2(unit_price * D(row["quantity"]))
                total += line_total
                conn.execute(
                    "UPDATE quote_item SET unit_price = ?, line_total = ? WHERE id = ?",
                    (str(unit_price), str(line_total), row["id"]),
                )
            conn.execute(
                "UPDATE quote SET profit_rate = ?, total_amount = ? WHERE id = ?",
                (str(q2(rate)), str(q2(total)), quote_id),
            )

    def apply_quote_shipping_amount(self, quote_id: int, shipping_amount: Any) -> None:
        amount = q2(shipping_amount)
        if amount < 0:
            raise ValueError("Nakliye tutarı negatif olamaz.")
        with db.tx() as conn:
            quote = conn.execute("SELECT id FROM quote WHERE id = ?", (quote_id,)).fetchone()
            if not quote:
                raise ValueError("Teklif bulunamadı.")
            conn.execute(
                "UPDATE quote SET shipping_amount = ?, parasut_offer_id = NULL, status = 'review' WHERE id = ?",
                (str(amount), quote_id),
            )
            self._refresh_quote_total(conn, quote_id)

    def reset_quote_parasut(self, quote_id: int) -> None:
        with db.tx() as conn:
            conn.execute(
                "UPDATE quote SET parasut_offer_id = NULL, status = 'review' WHERE id = ?",
                (quote_id,),
            )

    def mark_quote_sent_to_parasut(self, quote_id: int, parasut_offer_id: str) -> None:
        with db.tx() as conn:
            conn.execute(
                "UPDATE quote SET parasut_offer_id = ?, status = 'sent_to_parasut' WHERE id = ?",
                (parasut_offer_id, quote_id),
            )

    def list_quotes(self) -> list[sqlite3.Row]:
        with db.connect() as conn:
            return conn.execute("SELECT * FROM quote ORDER BY id DESC").fetchall()

    def get_quote(self, quote_id: int) -> tuple[sqlite3.Row, list[sqlite3.Row]]:
        with db.connect() as conn:
            quote = conn.execute("SELECT * FROM quote WHERE id = ?", (quote_id,)).fetchone()
            if not quote:
                raise ValueError("Teklif bulunamadı.")
            items = conn.execute("SELECT * FROM quote_item WHERE quote_id = ? ORDER BY id", (quote_id,)).fetchall()
            return quote, items

    def serialize_quote(self, quote: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": quote["id"],
            "customer_name": quote["customer_name"],
            "profit_rate": float(quote["profit_rate"] or 0),
            "shipping_amount": float(quote["shipping_amount"] or 0),
            "total_amount": float(quote["total_amount"] or 0),
            "status": quote["status"],
            "parasut_offer_id": quote["parasut_offer_id"],
            "created_at": quote["created_at"],
        }

    def serialize_quote_item(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "quote_id": row["quote_id"],
            "part_code": row["part_code"],
            "part_name": row["part_name"],
            "quantity": row["quantity"],
            "unit_cost": float(row["unit_cost"] or 0),
            "unit_price": float(row["unit_price"] or 0),
            "line_total": float(row["line_total"] or 0),
            "cut_area_m2": float(row["cut_area_m2"] or 0),
            "weight_kg": float(row["weight_kg"] or 0),
            "inputs": loads_json(row["inputs_json"], {}),
            "result": loads_json(row["result_json"], {}),
        }

    def serialize_cart_item(self, row: sqlite3.Row) -> dict[str, Any]:
        return {"id": row["id"], "part_code": row["part_code"], "quantity": row["quantity"], "inputs": loads_json(row["inputs_json"], {})}


repository = Repository()
