"""
generate_data.py
-----------------
Generates a synthetic but realistic consumer-electronics supply chain
dataset by RUNNING A DAILY SIMULATION (not just random sampling).

Why simulate instead of randomly sampling rows?
Random sampling gives you numbers that don't relate to each other.
A simulation makes inventory actually go up when a shipment arrives
and down when a sale happens -- so the KPIs you calculate later
(fulfillment rate, turnover, lead time, stock-outs) tell a real,
internally-consistent story, the same way they would from a real
company's data.

Output: five CSVs written to ./data/
  - suppliers.csv
  - warehouses.csv
  - products.csv
  - purchase_orders.csv   (one row per PO, with promised vs actual delivery)
  - daily_ops.csv         (one row per warehouse-product-day: demand,
                            fulfilled qty, stock-outs, ending inventory)
"""

import numpy as np
import pandas as pd
from datetime import date, timedelta

RNG = np.random.default_rng(42)  # fixed seed = reproducible dataset
START_DATE = date(2024, 1, 1)
END_DATE = date(2025, 12, 31)
DATES = pd.date_range(START_DATE, END_DATE, freq="D")
N_DAYS = len(DATES)

OUT_DIR = "data"
import os
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------
# 1. SUPPLIERS
# ---------------------------------------------------------------------
SUPPLIER_REGIONS = ["China", "Vietnam", "Taiwan", "South Korea", "Mexico", "USA", "Germany", "India"]
N_SUPPLIERS = 28

suppliers = pd.DataFrame({
    "supplier_id": [f"SUP-{i:03d}" for i in range(1, N_SUPPLIERS + 1)],
    "supplier_name": [f"{RNG.choice(['Global','Pacific','Sino','Nova','Apex','Summit','Prime','United'])} "
                       f"{RNG.choice(['Electronics','Components','Manufacturing','Industries','Tech'])} "
                       f"{i}" for i in range(1, N_SUPPLIERS + 1)],
    "region": RNG.choice(SUPPLIER_REGIONS, N_SUPPLIERS),
})
# Base lead time varies by region (distance/customs realism)
region_base_lead = {"China": 28, "Vietnam": 26, "Taiwan": 22, "South Korea": 20,
                     "Mexico": 10, "USA": 6, "Germany": 14, "India": 24}
suppliers["base_lead_time_days"] = suppliers["region"].map(region_base_lead) + RNG.integers(-3, 4, N_SUPPLIERS)
# Reliability: 0.75-0.99, higher = fewer/shorter delays. A handful of suppliers are deliberately bad.
suppliers["reliability_score"] = np.clip(RNG.normal(0.90, 0.07, N_SUPPLIERS), 0.55, 0.99).round(2)
suppliers.to_csv(f"{OUT_DIR}/suppliers.csv", index=False)

# ---------------------------------------------------------------------
# 2. WAREHOUSES
# ---------------------------------------------------------------------
warehouses = pd.DataFrame({
    "warehouse_id": ["WH-EAST", "WH-WEST", "WH-CENTRAL", "WH-EU", "WH-APAC"],
    "warehouse_name": ["East Coast DC", "West Coast DC", "Central DC", "EU Fulfillment Center", "APAC Fulfillment Center"],
    "region": ["North America", "North America", "North America", "Europe", "Asia Pacific"],
})
warehouses.to_csv(f"{OUT_DIR}/warehouses.csv", index=False)

# ---------------------------------------------------------------------
# 3. PRODUCTS
# ---------------------------------------------------------------------
CATEGORIES = {
    "Audio": ["Wireless Earbuds Pro", "Noise-Cancelling Headphones", "Bluetooth Speaker Mini", "Soundbar 2.1"],
    "Wearables": ["Fitness Tracker X", "Smartwatch Series 3", "Sleep Ring"],
    "Charging": ["65W GaN Charger", "Wireless Charging Pad", "Power Bank 20K"],
    "Smart Home": ["Smart Plug", "Video Doorbell", "Smart Bulb 4-Pack"],
    "Accessories": ["USB-C Cable 2m", "Laptop Stand", "Phone Case Armor", "Screen Protector 3-Pack"],
}
product_rows = []
pid = 1
for cat, names in CATEGORIES.items():
    for name in names:
        for variant in range(1, RNG.integers(2, 4)):  # a couple SKUs per product line
            product_rows.append({
                "product_id": f"PRD-{pid:04d}",
                "product_name": f"{name} v{variant}",
                "category": cat,
                "unit_cost": round(RNG.uniform(4, 60), 2),
                "supplier_id": suppliers.sample(1, random_state=int(RNG.integers(0, 1_000_000)))["supplier_id"].iloc[0],
                "reorder_point": int(RNG.integers(80, 250)),
                "reorder_qty": int(RNG.integers(400, 1200)),
                "base_daily_demand": round(RNG.uniform(2, 18), 1),
            })
            pid += 1
products = pd.DataFrame(product_rows)
products["unit_price"] = (products["unit_cost"] * RNG.uniform(2.0, 3.2, len(products))).round(2)
products.to_csv(f"{OUT_DIR}/products.csv", index=False)

N_PRODUCTS = len(products)
print(f"Generated {N_SUPPLIERS} suppliers, {len(warehouses)} warehouses, {N_PRODUCTS} products.")

# ---------------------------------------------------------------------
# 4 & 5. SIMULATE PURCHASE ORDERS + DAILY INVENTORY/SALES PER WAREHOUSE-PRODUCT
# ---------------------------------------------------------------------
sup_lookup = suppliers.set_index("supplier_id")[["base_lead_time_days", "reliability_score"]]

def seasonal_multiplier(d: pd.Timestamp) -> float:
    """Holiday bump in Nov/Dec, back-to-school bump in Aug/Sep, slow Feb."""
    m = d.month
    if m in (11, 12):
        return 1.9 if m == 11 and d.day >= 20 else (2.3 if m == 12 and d.day <= 25 else 1.6)
    if m in (8, 9):
        return 1.3
    if m == 2:
        return 0.8
    return 1.0

po_rows = []
daily_rows = []
po_counter = 1

for _, wh in warehouses.iterrows():
    wh_id = wh["warehouse_id"]
    # not every product is stocked at every warehouse; ~70% coverage
    stocked_products = products.sample(frac=0.7, random_state=int(RNG.integers(0, 1_000_000)))

    for _, prod in stocked_products.iterrows():
        prod_id = prod["product_id"]
        sup_id = prod["supplier_id"]
        base_lead = int(sup_lookup.loc[sup_id, "base_lead_time_days"])
        reliability = float(sup_lookup.loc[sup_id, "reliability_score"])

        stock = int(RNG.integers(prod["reorder_qty"] * 0.6, prod["reorder_qty"] * 1.2))
        reorder_point = prod["reorder_point"]
        reorder_qty = prod["reorder_qty"]
        base_demand = prod["base_daily_demand"]

        pending_pos = []  # list of (arrival_date, qty)

        for d in DATES:
            # --- receive any POs arriving today ---
            arriving = [p for p in pending_pos if p[0] == d]
            for p in arriving:
                stock += p[1]
            pending_pos = [p for p in pending_pos if p[0] != d]

            # --- today's demand ---
            mult = seasonal_multiplier(d)
            demand = max(0, int(round(RNG.normal(base_demand * mult, base_demand * 0.35))))

            fulfilled = min(demand, stock)
            stockout_flag = 1 if demand > stock else 0
            stock -= fulfilled

            daily_rows.append((d, wh_id, prod_id, demand, fulfilled, stockout_flag, stock))

            # --- reorder logic ---
            if stock <= reorder_point and not any(True for _ in pending_pos) and d <= pd.Timestamp(END_DATE) - timedelta(days=5):
                # supplier reliability drives delay: unreliable suppliers run later, more variably
                delay = 0
                if RNG.random() > reliability:
                    delay = int(RNG.integers(3, 25))
                actual_lead = max(1, base_lead + delay + int(RNG.integers(-2, 3)))
                order_date = d
                promised_date = order_date + timedelta(days=base_lead)
                actual_date = order_date + timedelta(days=actual_lead)
                pending_pos.append((actual_date, reorder_qty))
                po_rows.append((
                    f"PO-{po_counter:06d}", order_date.date(), sup_id, wh_id, prod_id,
                    reorder_qty, base_lead, promised_date.date(), actual_date.date(),
                    (actual_date - promised_date).days
                ))
                po_counter += 1

print("Simulation complete. Writing CSVs...")

purchase_orders = pd.DataFrame(po_rows, columns=[
    "po_id", "order_date", "supplier_id", "warehouse_id", "product_id",
    "quantity_ordered", "promised_lead_time_days", "promised_delivery_date",
    "actual_delivery_date", "delay_days"
])
purchase_orders.to_csv(f"{OUT_DIR}/purchase_orders.csv", index=False)

daily_ops = pd.DataFrame(daily_rows, columns=[
    "date", "warehouse_id", "product_id", "units_demanded", "units_fulfilled",
    "stockout_flag", "ending_inventory"
])
daily_ops.to_csv(f"{OUT_DIR}/daily_ops.csv", index=False)

print(f"purchase_orders.csv: {len(purchase_orders):,} rows")
print(f"daily_ops.csv: {len(daily_ops):,} rows")
print("Done. Data written to ./data/")
