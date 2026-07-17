from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.config import sqlite_path


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS material (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    unit TEXT NOT NULL CHECK(unit IN ('m','adet','m2','kg'))
);

CREATE TABLE IF NOT EXISTS material_option (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL REFERENCES material(id) ON DELETE CASCADE,
    option_name TEXT NOT NULL,
    quantity NUMERIC NOT NULL DEFAULT 0,
    average_unit_cost NUMERIC NOT NULL DEFAULT 0,
    is_available INTEGER NOT NULL DEFAULT 1 CHECK(is_available IN (0, 1))
);

CREATE TABLE IF NOT EXISTS customer_session (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_token TEXT NOT NULL UNIQUE,
    whatsapp_phone TEXT,
    parasut_contact_id TEXT,
    customer_name TEXT,
    pending_action TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES customer_session(id) ON DELETE SET NULL,
    cart_token TEXT UNIQUE,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','converted','cancelled')),
    customer_name TEXT,
    shipping_amount NUMERIC NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cart_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cart_id INTEGER NOT NULL REFERENCES cart(id) ON DELETE CASCADE,
    part_code TEXT NOT NULL,
    inputs_json TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quote (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cart_id INTEGER REFERENCES cart(id) ON DELETE SET NULL,
    parasut_offer_id TEXT,
    customer_name TEXT NOT NULL,
    profit_rate NUMERIC NOT NULL DEFAULT 0,
    shipping_amount NUMERIC NOT NULL DEFAULT 0,
    total_amount NUMERIC NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','review','sent','approved','rejected','sent_to_parasut','merged')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS round_part_price (
    part_code TEXT NOT NULL,
    cap_mm INTEGER NOT NULL,
    price NUMERIC NOT NULL DEFAULT 0,
    PRIMARY KEY (part_code, cap_mm)
);

CREATE TABLE IF NOT EXISTS quote_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quote_id INTEGER NOT NULL REFERENCES quote(id) ON DELETE CASCADE,
    part_code TEXT NOT NULL,
    part_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_cost NUMERIC NOT NULL DEFAULT 0,
    unit_price NUMERIC NOT NULL DEFAULT 0,
    line_total NUMERIC NOT NULL DEFAULT 0,
    cut_area_m2 NUMERIC NOT NULL DEFAULT 0,
    weight_kg NUMERIC NOT NULL DEFAULT 0,
    inputs_json TEXT NOT NULL,
    result_json TEXT NOT NULL
);
"""

MIGRATIONS_SQL = [

    "ALTER TABLE quote ADD COLUMN profit_rate NUMERIC NOT NULL DEFAULT 0",
    "ALTER TABLE customer_session ADD COLUMN pending_action TEXT",
    "ALTER TABLE cart ADD COLUMN cart_token TEXT",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_cart_cart_token ON cart(cart_token)",
    "ALTER TABLE material_option ADD COLUMN is_available INTEGER NOT NULL DEFAULT 1 CHECK(is_available IN (0, 1))",
    "INSERT OR IGNORE INTO material(name, unit) SELECT 'BOYA', 'm2' WHERE NOT EXISTS (SELECT 1 FROM material WHERE name = 'BOYA')",
    "INSERT OR IGNORE INTO material_option(material_id, option_name, quantity, average_unit_cost) SELECT id, 'Standart', 1000, 50 FROM material WHERE name = 'BOYA' AND NOT EXISTS (SELECT 1 FROM material_option mo JOIN material m ON m.id = mo.material_id WHERE m.name = 'BOYA')",
    "INSERT INTO material(name, unit) SELECT 'IZOLASYON', 'm2' WHERE NOT EXISTS (SELECT 1 FROM material WHERE name = 'IZOLASYON')",
    "INSERT INTO material_option(material_id, option_name, quantity, average_unit_cost) SELECT id, '19mm Kauçuk', 1000, 150 FROM material WHERE name = 'IZOLASYON' AND NOT EXISTS (SELECT 1 FROM material_option mo JOIN material m ON m.id = mo.material_id WHERE m.name = 'IZOLASYON' AND mo.option_name = '19mm Kauçuk')",
    "INSERT INTO material_option(material_id, option_name, quantity, average_unit_cost) SELECT id, '25mm Kauçuk', 1000, 200 FROM material WHERE name = 'IZOLASYON' AND NOT EXISTS (SELECT 1 FROM material_option mo JOIN material m ON m.id = mo.material_id WHERE m.name = 'IZOLASYON' AND mo.option_name = '25mm Kauçuk')",

    "INSERT OR IGNORE INTO material(name, unit) SELECT 'SAC', 'kg' WHERE NOT EXISTS (SELECT 1 FROM material WHERE name = 'SAC')",
    "INSERT OR IGNORE INTO material_option(material_id, option_name, quantity, average_unit_cost) SELECT id, '0.50 mm', 1000, 45 FROM material WHERE name = 'SAC' AND NOT EXISTS (SELECT 1 FROM material_option mo JOIN material m ON m.id = mo.material_id WHERE m.name = 'SAC' AND mo.option_name = '0.50 mm')",
    "INSERT OR IGNORE INTO material_option(material_id, option_name, quantity, average_unit_cost) SELECT id, '0.60 mm', 1000, 48 FROM material WHERE name = 'SAC' AND NOT EXISTS (SELECT 1 FROM material_option mo JOIN material m ON m.id = mo.material_id WHERE m.name = 'SAC' AND mo.option_name = '0.60 mm')",
    "INSERT OR IGNORE INTO material_option(material_id, option_name, quantity, average_unit_cost) SELECT id, '0.65 mm', 1000, 50 FROM material WHERE name = 'SAC' AND NOT EXISTS (SELECT 1 FROM material_option mo JOIN material m ON m.id = mo.material_id WHERE m.name = 'SAC' AND mo.option_name = '0.65 mm')",
    "INSERT OR IGNORE INTO material_option(material_id, option_name, quantity, average_unit_cost) SELECT id, '0.70 mm', 1000, 52 FROM material WHERE name = 'SAC' AND NOT EXISTS (SELECT 1 FROM material_option mo JOIN material m ON m.id = mo.material_id WHERE m.name = 'SAC' AND mo.option_name = '0.70 mm')",
    "INSERT OR IGNORE INTO material_option(material_id, option_name, quantity, average_unit_cost) SELECT id, '0.80 mm', 1000, 55 FROM material WHERE name = 'SAC' AND NOT EXISTS (SELECT 1 FROM material_option mo JOIN material m ON m.id = mo.material_id WHERE m.name = 'SAC' AND mo.option_name = '0.80 mm')",
    "INSERT OR IGNORE INTO material(name, unit) SELECT 'FLANS', 'm' WHERE NOT EXISTS (SELECT 1 FROM material WHERE name = 'FLANS')",
    "INSERT OR IGNORE INTO material_option(material_id, option_name, quantity, average_unit_cost) SELECT id, 'Standart', 1000, 25 FROM material WHERE name = 'FLANS' AND NOT EXISTS (SELECT 1 FROM material_option mo JOIN material m ON m.id = mo.material_id WHERE m.name = 'FLANS')",
    "INSERT OR IGNORE INTO material(name, unit) SELECT 'CONTA', 'm' WHERE NOT EXISTS (SELECT 1 FROM material WHERE name = 'CONTA')",
    "INSERT OR IGNORE INTO material_option(material_id, option_name, quantity, average_unit_cost) SELECT id, 'Standart', 1000, 8 FROM material WHERE name = 'CONTA' AND NOT EXISTS (SELECT 1 FROM material_option mo JOIN material m ON m.id = mo.material_id WHERE m.name = 'CONTA')",
    "INSERT OR IGNORE INTO material(name, unit) SELECT 'VIDA', 'adet' WHERE NOT EXISTS (SELECT 1 FROM material WHERE name = 'VIDA')",
    "INSERT OR IGNORE INTO material_option(material_id, option_name, quantity, average_unit_cost) SELECT id, 'Standart', 1000, 0.5 FROM material WHERE name = 'VIDA' AND NOT EXISTS (SELECT 1 FROM material_option mo JOIN material m ON m.id = mo.material_id WHERE m.name = 'VIDA')",
]


class Database:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or sqlite_path()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            self._ensure_quote_merged_status(conn)
            for sql in MIGRATIONS_SQL:
                try:
                    conn.execute(sql)
                except sqlite3.OperationalError as exc:
                    if "duplicate column name" not in str(exc).lower():
                        raise
            conn.commit()

    def _ensure_quote_merged_status(self, conn: sqlite3.Connection) -> None:
        row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'quote'").fetchone()
        if not row or "'merged'" in (row["sql"] or ""):
            return
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("ALTER TABLE quote RENAME TO quote_old")
        conn.execute(
            """
            CREATE TABLE quote (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cart_id INTEGER REFERENCES cart(id) ON DELETE SET NULL,
                parasut_offer_id TEXT,
                customer_name TEXT NOT NULL,
                profit_rate NUMERIC NOT NULL DEFAULT 0,
                shipping_amount NUMERIC NOT NULL DEFAULT 0,
                total_amount NUMERIC NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','review','sent','approved','rejected','sent_to_parasut','merged')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            INSERT INTO quote(id, cart_id, parasut_offer_id, customer_name, profit_rate, shipping_amount, total_amount, status, created_at)
            SELECT id, cart_id, parasut_offer_id, customer_name, profit_rate, shipping_amount, total_amount, status, created_at
            FROM quote_old
            """
        )
        conn.execute("DROP TABLE quote_old")
        self._ensure_quote_item_quote_fk(conn)
        conn.execute("PRAGMA foreign_keys = ON")

    def _ensure_quote_item_quote_fk(self, conn: sqlite3.Connection) -> None:
        row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'quote_item'").fetchone()
        if not row or "quote_old" not in (row["sql"] or ""):
            return
        conn.execute("ALTER TABLE quote_item RENAME TO quote_item_old")
        conn.execute(
            """
            CREATE TABLE quote_item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_id INTEGER NOT NULL REFERENCES quote(id) ON DELETE CASCADE,
                part_code TEXT NOT NULL,
                part_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_cost NUMERIC NOT NULL DEFAULT 0,
                unit_price NUMERIC NOT NULL DEFAULT 0,
                line_total NUMERIC NOT NULL DEFAULT 0,
                cut_area_m2 NUMERIC NOT NULL DEFAULT 0,
                weight_kg NUMERIC NOT NULL DEFAULT 0,
                inputs_json TEXT NOT NULL,
                result_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO quote_item(id, quote_id, part_code, part_name, quantity, unit_cost, unit_price, line_total, cut_area_m2, weight_kg, inputs_json, result_json)
            SELECT id, quote_id, part_code, part_name, quantity, unit_cost, unit_price, line_total, cut_area_m2, weight_kg, inputs_json, result_json
            FROM quote_item_old
            """
        )
        conn.execute("DROP TABLE quote_item_old")

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


db = Database()
