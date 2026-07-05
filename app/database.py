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
    average_unit_cost NUMERIC NOT NULL DEFAULT 0
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
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','review','sent','approved','rejected','sent_to_parasut')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
            for sql in MIGRATIONS_SQL:
                try:
                    conn.execute(sql)
                except sqlite3.OperationalError as exc:
                    if "duplicate column name" not in str(exc).lower():
                        raise
            conn.commit()

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


db = Database()
