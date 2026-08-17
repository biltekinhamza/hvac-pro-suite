from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from typing import Any

from fastapi.encoders import jsonable_encoder

from app.database import db
from app.utils import dumps_json, q2


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class MobileRepository:
    def activate(self, tenant_id: str, device_id: str, device_name: str) -> str:
        token = secrets.token_urlsafe(32)
        digest = token_hash(token)
        with db.tx() as conn:
            conn.execute(
                """
                INSERT INTO mobile_device(tenant_id, device_id, device_name, token_hash)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(tenant_id, device_id) DO UPDATE SET
                    device_name=excluded.device_name,
                    token_hash=excluded.token_hash,
                    last_activated_at=CURRENT_TIMESTAMP
                """,
                (tenant_id, device_id, device_name, digest),
            )
        return token

    def device_for_token(self, token: str) -> sqlite3.Row | None:
        with db.connect() as conn:
            return conn.execute(
                "SELECT id, tenant_id, device_id, device_name FROM mobile_device WHERE token_hash = ?",
                (token_hash(token),),
            ).fetchone()

    def run_operation(
        self,
        device: sqlite3.Row,
        operation_id: str,
        operation_type: str,
        draft: dict[str, Any],
        prepared_items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        canonical = json.dumps(
            jsonable_encoder({"type": operation_type, "draft": draft}),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        request_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        with db.tx() as conn:
            existing = conn.execute(
                "SELECT device_id, request_hash, result_json FROM mobile_operation WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
            if existing:
                if existing["device_id"] != device["id"] or existing["request_hash"] != request_hash:
                    raise ValueError("operation_id daha once farkli bir istek icin kullanildi.")
                result = json.loads(existing["result_json"])
                result["replayed"] = True
                return result

            cart = self._replace_draft_cart(conn, device, draft)
            if operation_type == "sync_draft":
                result = {"ok": True, "type": operation_type, "draft_id": draft["local_id"], "cart_id": cart["id"], "replayed": False}
            else:
                if not prepared_items:
                    raise ValueError("Teklif icin en az bir kalem gerekli.")
                quote_id, total = self._create_quote(conn, cart, draft, prepared_items)
                result = {"ok": True, "type": operation_type, "draft_id": draft["local_id"], "quote_id": quote_id, "total_amount": float(total), "replayed": False}

            conn.execute(
                "INSERT INTO mobile_operation(operation_id, device_id, request_hash, operation_type, result_json) VALUES(?, ?, ?, ?, ?)",
                (operation_id, device["id"], request_hash, operation_type, dumps_json(result)),
            )
            return result

    def _replace_draft_cart(self, conn: sqlite3.Connection, device: sqlite3.Row, draft: dict[str, Any]) -> sqlite3.Row:
        mapping = conn.execute(
            "SELECT cart_id FROM mobile_draft WHERE device_id = ? AND local_id = ?",
            (device["id"], draft["local_id"]),
        ).fetchone()
        cart = conn.execute("SELECT * FROM cart WHERE id = ? AND status = 'active'", (mapping["cart_id"],)).fetchone() if mapping else None
        if not cart:
            cart_token = "mobile_" + secrets.token_urlsafe(24)
            cursor = conn.execute(
                "INSERT INTO cart(cart_token, status, customer_name, customer_phone, shipping_amount) VALUES(?, 'active', ?, ?, ?)",
                (cart_token, draft["customer_name"].strip(), draft["customer_phone"].strip(), str(q2(draft["shipping_amount"]))),
            )
            cart_id = int(cursor.lastrowid)
            conn.execute(
                "INSERT INTO mobile_draft(device_id, local_id, cart_id) VALUES(?, ?, ?) ON CONFLICT(device_id, local_id) DO UPDATE SET cart_id=excluded.cart_id, updated_at=CURRENT_TIMESTAMP",
                (device["id"], draft["local_id"], cart_id),
            )
            cart = conn.execute("SELECT * FROM cart WHERE id = ?", (cart_id,)).fetchone()
        else:
            conn.execute(
                "UPDATE cart SET customer_name = ?, customer_phone = ?, shipping_amount = ? WHERE id = ?",
                (draft["customer_name"].strip(), draft["customer_phone"].strip(), str(q2(draft["shipping_amount"])), cart["id"]),
            )
            conn.execute("UPDATE mobile_draft SET updated_at=CURRENT_TIMESTAMP WHERE device_id=? AND local_id=?", (device["id"], draft["local_id"]))

        conn.execute("DELETE FROM cart_item WHERE cart_id = ?", (cart["id"],))
        conn.executemany(
            "INSERT INTO cart_item(cart_id, part_code, inputs_json, quantity) VALUES(?, ?, ?, ?)",
            [(cart["id"], item["part_code"], dumps_json(item["inputs"]), item["quantity"]) for item in draft["items"]],
        )
        return cart

    def _create_quote(self, conn: sqlite3.Connection, cart: sqlite3.Row, draft: dict[str, Any], items: list[dict[str, Any]]) -> tuple[int, Any]:
        cursor = conn.execute(
            "INSERT INTO quote(cart_id, customer_name, customer_phone, profit_rate, shipping_amount, total_amount, status) VALUES(?, ?, ?, ?, ?, 0, 'review')",
            (cart["id"], draft["customer_name"].strip() or "Genel Musteri", draft["customer_phone"].strip(), str(q2(draft["profit_rate"])), str(q2(draft["shipping_amount"]))),
        )
        quote_id = int(cursor.lastrowid)
        total = q2(draft["shipping_amount"])
        for item in items:
            conn.execute(
                """
                INSERT INTO quote_item(quote_id, part_code, part_name, quantity, unit_cost, unit_price,
                    line_total, cut_area_m2, weight_kg, inputs_json, result_json)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (quote_id, item["part_code"], item["part_name"], item["quantity"], str(q2(item["unit_cost"])),
                 str(q2(item["unit_price"])), str(q2(item["line_total"])), str(item["cut_area_m2"]),
                 str(item["weight_kg"]), dumps_json(item["inputs"]), dumps_json(item["result"])),
            )
            total += q2(item["line_total"])
        conn.execute("UPDATE quote SET total_amount = ? WHERE id = ?", (str(q2(total)), quote_id))
        conn.execute("UPDATE cart SET status='converted', cart_token=NULL WHERE id = ?", (cart["id"],))
        conn.execute("DELETE FROM mobile_draft WHERE device_id = ? AND local_id = ?", (draft["device_db_id"], draft["local_id"]))
        return quote_id, q2(total)


mobile_repository = MobileRepository()
