import sqlite3
import json

db_path = "data/whatsapp_bot.sqlite3"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

for qid in [99, 101]:
    print(f"\n{'='*60}")
    print(f"QUOTE #{qid}")
    print(f"{'='*60}")
    cursor.execute("SELECT * FROM quote WHERE id = ?", (qid,))
    row = cursor.fetchone()
    if row:
        for key in row.keys():
            print(f"  {key}: {row[key]}")
    
    cursor.execute("SELECT * FROM quote_item WHERE quote_id = ?", (qid,))
    items = cursor.fetchall()
    print(f"\n  Items ({len(items)}):")
    for item in items:
        print(f"  ---")
        for key in item.keys():
            print(f"    {key}: {item[key]}")

conn.close()
