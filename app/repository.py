from __future__ import annotations

import sqlite3
import secrets
from pathlib import Path
from typing import Any

from app.config import BASE_DIR
from app.database import db
from app.utils import D, dumps_json, loads_json, q2


class Repository:
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
                SELECT mo.id, mo.option_name, mo.quantity, mo.average_unit_cost, m.name, m.unit
                FROM material_option mo
                JOIN material m ON m.id = mo.material_id
                WHERE mo.id = ?
                """,
                (option_id,),
            ).fetchone()
            if not row:
                raise ValueError("Malzeme özelliği bulunamadı.")
            return row

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
        text = str(thickness or "").strip()
        if not text:
            return self.find_first_option_by_name("SAC")
        return self.find_option_by_name_and_option("KARE KANAL SAC", text) or self.find_option_by_name_and_option("SAC", text)

    def list_material_options(self) -> list[sqlite3.Row]:
        with db.connect() as conn:
            return conn.execute(
                """
                SELECT mo.id, m.name, mo.option_name, m.unit, mo.quantity, mo.average_unit_cost
                FROM material_option mo
                JOIN material m ON m.id = mo.material_id
                ORDER BY m.name, mo.option_name
                """
            ).fetchall()

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
                SELECT mo.id, m.name, mo.option_name, m.unit, mo.quantity, mo.average_unit_cost
                FROM material_option mo
                JOIN material m ON m.id = mo.material_id
                WHERE mo.id = ?
                """,
                (option_id,),
            ).fetchone()

    def get_active_cart(self) -> sqlite3.Row:
        with db.tx() as conn:
            row = conn.execute("SELECT * FROM cart WHERE status='active' ORDER BY id DESC LIMIT 1").fetchone()
            if row:
                return row
            conn.execute("INSERT INTO cart(status, customer_name, shipping_amount) VALUES('active', '', 0)")
            return conn.execute("SELECT * FROM cart WHERE status='active' ORDER BY id DESC LIMIT 1").fetchone()

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

    def add_cart_item(self, part_code: str, inputs: dict[str, Any], quantity: int) -> int:
        cart = self.get_active_cart()
        with db.tx() as conn:
            cur = conn.execute(
                "INSERT INTO cart_item(cart_id, part_code, inputs_json, quantity) VALUES(?, ?, ?, ?)",
                (cart["id"], part_code, dumps_json(inputs), quantity),
            )
            return int(cur.lastrowid)

    def list_cart_items(self) -> list[sqlite3.Row]:
        cart = self.get_active_cart()
        with db.connect() as conn:
            return conn.execute("SELECT * FROM cart_item WHERE cart_id = ? ORDER BY id", (cart["id"],)).fetchall()

    def create_quote(self, customer_name: str, shipping_amount: Any, items: list[dict[str, Any]]) -> int:
        cart = self.get_active_cart()
        with db.tx() as conn:
            cur = conn.execute(
                "INSERT INTO quote(cart_id, customer_name, profit_rate, shipping_amount, total_amount, status) VALUES(?, ?, 0, ?, 0, 'review')",
                (cart["id"], customer_name.strip() or "Genel Müşteri", str(q2(shipping_amount))),
            )
            quote_id = int(cur.lastrowid)
            total = D("0")
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
            conn.execute("UPDATE cart SET status='converted' WHERE id = ?", (cart["id"],))
            conn.execute("INSERT INTO cart(status, customer_name, shipping_amount) VALUES('active', '', 0)")
            return quote_id

    def apply_quote_profit_rate(self, quote_id: int, profit_rate: Any) -> None:
        rate = D(profit_rate)
        with db.tx() as conn:
            quote = conn.execute("SELECT id FROM quote WHERE id = ?", (quote_id,)).fetchone()
            if not quote:
                raise ValueError("Teklif bulunamadı.")
            rows = conn.execute("SELECT id, unit_cost, quantity FROM quote_item WHERE quote_id = ?", (quote_id,)).fetchall()
            total = D("0")
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
