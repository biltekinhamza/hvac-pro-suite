#!/usr/bin/env python3
"""
Recalculate quote #99 with all parts using 0.80mm sheet metal
and create a new quote with updated prices.
"""

import sys
sys.path.insert(0, r"C:\Users\TavSan\Desktop\HVAC Pro Suite")

from decimal import Decimal
from app.database import db
from app.repository import repository
from app.ventilation.engine import CostEngine
from app.utils import D, q2, dumps_json, loads_json


def main():
    engine = CostEngine(repository)
    profit_rate = Decimal("20")
    
    # Get quote #99 items
    with db.connect() as conn:
        quote = conn.execute("SELECT * FROM quote WHERE id = 99").fetchone()
        if not quote:
            print("Quote #99 not found!")
            return
        
        items = conn.execute("SELECT * FROM quote_item WHERE quote_id = 99 ORDER BY id").fetchall()
    
    print(f"Original Quote: {quote['customer_name']} - {quote['total_amount']} TL")
    print(f"Items found: {len(items)}")
    print()
    
    new_items = []
    total_new = Decimal("0")
    
    for item in items:
        inputs = loads_json(item["inputs_json"], {})
        
        # Update sheet thickness to 0.80mm
        inputs["sac_kalinlik_mm"] = "0.80"
        inputs["sac_ozellik_id"] = ""  # Let engine find the 0.80mm option
        
        part_code = item["part_code"]
        quantity = item["quantity"]
        
        # Recalculate geometry and cost
        result = engine.calculate(part_code, inputs)
        sale = engine.calculate_sale(result, profit_rate, quantity)
        
        new_item = {
            "part_code": part_code,
            "part_name": item["part_name"],
            "quantity": quantity,
            "unit_cost": sale["unit_cost"],
            "unit_price": sale["unit_price"],
            "line_total": sale["line_total"],
            "cut_area_m2": result.get("kesilen_m2", 0),
            "weight_kg": result.get("kg", 0),
            "inputs": inputs,
            "result": result,
        }
        
        new_items.append(new_item)
        total_new += D(sale["line_total"])
        
        print(f"{part_code} x{quantity}:")
        print(f"  Old: {item['unit_cost']} -> New: {sale['unit_cost']} (cost)")
        print(f"  Old: {item['unit_price']} -> New: {sale['unit_price']} (price)")
        print(f"  Line total: {sale['line_total']}")
        print()
    
    # Add shipping amount from original quote
    shipping = D(quote["shipping_amount"])
    total_with_shipping = total_new + shipping
    
    print(f"Subtotal: {total_new}")
    print(f"Shipping: {shipping}")
    print(f"Total: {total_with_shipping}")
    print()
    
    # Create new quote
    new_quote_id = repository.create_quote_from_items(
        customer_name=quote["customer_name"],
        profit_rate=profit_rate,
        shipping_amount=shipping,
        items=new_items
    )
    
    print(f"✓ New quote created: #{new_quote_id}")
    print(f"  Customer: {quote['customer_name']}")
    print(f"  Total: {total_with_shipping} TL")
    print(f"  Profit rate: {profit_rate}%")
    

if __name__ == "__main__":
    main()