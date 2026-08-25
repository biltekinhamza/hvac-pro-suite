import sqlite3
import sys

db_path = "data/whatsapp_bot.sqlite3"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for t in tables:
    print(f"Table: {t[0]}")
    cursor.execute(f'PRAGMA table_info("{t[0]}")')
    cols = cursor.fetchall()
    for c in cols:
        print(f"  {c[1]} ({c[2]})")

conn.close()
