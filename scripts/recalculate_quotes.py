from __future__ import annotations

import json

from app.database import db
from app.repository import repository
from app.utils import dumps_json, q2
from app.ventilation.engine import CostEngine


def recalculate_all_quotes() -> None:
    engine = CostEngine(repository)
    quotes = repository.list_quotes()
    updated_items = 0
    skipped: list[str] = []
    for quote_row in quotes:
        quote_id = quote_row["id"]
        profit_rate = quote_row["profit_rate"] or 0
        _, item_rows = repository.get_quote(quote_id)
        with db.tx() as conn:
            for row in item_rows:
                inputs = json.loads(row["inputs_json"]) if isinstance(row["inputs_json"], str) else row["inputs_json"]
                try:
                    result = engine.calculate(row["part_code"], inputs)
                    sale = engine.calculate_sale(result, profit_rate, row["quantity"])
                except (KeyError, ValueError, TypeError) as exc:
                    skipped.append(f"#{quote_id} kalem {row['id']} ({row['part_code']}): {exc}")
                    continue
                conn.execute(
                    """
                    UPDATE quote_item
                    SET unit_cost = ?, unit_price = ?, line_total = ?,
                        cut_area_m2 = ?, weight_kg = ?, result_json = ?
                    WHERE id = ?
                    """,
                    (
                        str(q2(sale["unit_cost"])),
                        str(q2(sale["unit_price"])),
                        str(q2(sale["line_total"])),
                        str(result["kesilen_m2"]),
                        str(result["kg"]),
                        dumps_json(result),
                        row["id"],
                    ),
                )
                updated_items += 1
            item_total = conn.execute(
                "SELECT COALESCE(SUM(line_total), 0) AS total FROM quote_item WHERE quote_id = ?",
                (quote_id,),
            ).fetchone()["total"]
            total = item_total + (quote_row["shipping_amount"] or 0)
            conn.execute(
                "UPDATE quote SET total_amount = ? WHERE id = ?",
                (str(q2(total)), quote_id),
            )
    print(f"{len(quotes)} teklif, {updated_items} kalem yeniden hesaplandı.")
    if skipped:
        print(f"{len(skipped)} kalem atlandı:")
        for line in skipped:
            print("  -", line)


if __name__ == "__main__":
    recalculate_all_quotes()
