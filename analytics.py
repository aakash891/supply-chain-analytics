"""
analytics.py
------------
Pure pandas functions that turn the raw simulated tables into the
KPIs a supply chain / ops analyst actually reports on. Each function
is intentionally small and documented with the BUSINESS DEFINITION
of the KPI, not just the code -- this is the part worth reading
closely if the goal is to actually learn the domain, not just ship
a dashboard.

All functions take pandas DataFrames in and return DataFrames out,
so they're easy to unit-test or call directly from a notebook,
independent of the Streamlit app.
"""

import pandas as pd


def order_fulfillment_rate(daily_ops: pd.DataFrame, group_cols=None) -> pd.DataFrame:
    """
    Order Fulfillment Rate = units actually shipped / units demanded.

    This is the single most-watched customer-facing supply chain KPI:
    it answers "when a customer wanted to buy something, could we
    actually give it to them?" Distinct from stock-out RATE (below),
    which counts *days* with a shortfall rather than *units* missed --
    fulfillment rate is unit-weighted, so one big miss on a
    high-demand day counts more than a tiny miss on a slow day.
    """
    cols = group_cols or []
    g = daily_ops.groupby(cols) if cols else daily_ops
    agg = g[["units_demanded", "units_fulfilled"]].sum().reset_index() if cols else \
        pd.DataFrame([g[["units_demanded", "units_fulfilled"]].sum()])
    agg["fulfillment_rate"] = (agg["units_fulfilled"] / agg["units_demanded"]).round(4)
    return agg


def stockout_rate(daily_ops: pd.DataFrame, group_cols=None) -> pd.DataFrame:
    """
    Stock-out Rate = % of (warehouse, product, day) combinations where
    demand exceeded available inventory.

    This is DAY-weighted, not unit-weighted -- it tells you how often
    a shortage happens at all, regardless of size. A product that
    stocks out for 1 unit short every day looks bad here even though
    it barely dents the fulfillment rate above. Ops teams track both
    because they diagnose different problems: fulfillment rate =
    "how much revenue/service did we lose", stockout rate = "how
    often does our replenishment process fail to keep up".
    """
    cols = group_cols or []
    g = daily_ops.groupby(cols) if cols else daily_ops
    agg = g["stockout_flag"].mean().reset_index() if cols else \
        pd.DataFrame([{"stockout_flag": daily_ops["stockout_flag"].mean()}])
    agg = agg.rename(columns={"stockout_flag": "stockout_rate"})
    agg["stockout_rate"] = agg["stockout_rate"].round(4)
    return agg


def average_lead_time(purchase_orders: pd.DataFrame, group_cols=None) -> pd.DataFrame:
    """
    Lead Time = days between placing a purchase order and physically
    receiving it (order_date -> actual_delivery_date).

    We report both the ACTUAL lead time (what really happened) and
    the delay vs PROMISED lead time, because a supplier with a long
    but predictable lead time is much easier to plan around than a
    supplier with a short lead time that's wildly unreliable. Lead
    time variance, not just the average, is often the more important
    number for setting safety stock / reorder points.
    """
    po = purchase_orders.copy()
    po["order_date"] = pd.to_datetime(po["order_date"])
    po["actual_delivery_date"] = pd.to_datetime(po["actual_delivery_date"])
    po["actual_lead_time_days"] = (po["actual_delivery_date"] - po["order_date"]).dt.days

    cols = group_cols or []
    g = po.groupby(cols) if cols else po
    agg = g.agg(
        avg_lead_time_days=("actual_lead_time_days", "mean"),
        lead_time_std_days=("actual_lead_time_days", "std"),
        avg_delay_days=("delay_days", "mean"),
        on_time_rate=("delay_days", lambda s: (s <= 0).mean()),
        po_count=("po_id", "count"),
    ).reset_index() if cols else pd.DataFrame([{
        "avg_lead_time_days": po["actual_lead_time_days"].mean(),
        "lead_time_std_days": po["actual_lead_time_days"].std(),
        "avg_delay_days": po["delay_days"].mean(),
        "on_time_rate": (po["delay_days"] <= 0).mean(),
        "po_count": len(po),
    }])
    for c in ["avg_lead_time_days", "lead_time_std_days", "avg_delay_days"]:
        agg[c] = agg[c].round(1)
    agg["on_time_rate"] = agg["on_time_rate"].round(3)
    return agg


def inventory_turnover(daily_ops: pd.DataFrame, products: pd.DataFrame,
                        group_cols=None, period_days: int = 365) -> pd.DataFrame:
    """
    Inventory Turnover = Cost of Goods Sold / Average Inventory Value,
    annualized.

    This is the classic "how efficiently is capital tied up in
    inventory being used" metric. High turnover = lean, fast-moving
    inventory (good, up to a point -- too high risks stock-outs).
    Low turnover = cash sitting on shelves, often paired with excess
    or obsolete stock. We compute it in DOLLAR terms (units * cost),
    not just unit counts, because that's how finance actually reads
    this KPI -- a warehouse full of $2 phone cases and one full of
    $50 smartwatches can have identical unit turnover but very
    different capital efficiency.
    """
    d = daily_ops.merge(products[["product_id", "unit_cost"]], on="product_id", how="left")
    d["cogs"] = d["units_fulfilled"] * d["unit_cost"]
    d["inventory_value"] = d["ending_inventory"] * d["unit_cost"]

    cols = group_cols or []

    # Step 1: total COGS per group over the whole window (numerator).
    cogs_agg = d.groupby(cols)["cogs"].sum().reset_index(name="total_cogs") if cols else \
        pd.DataFrame([{"total_cogs": d["cogs"].sum()}])
    n_days = d["date"].nunique()

    # Step 2: inventory VALUE MUST BE SUMMED ACROSS PRODUCTS/WAREHOUSES
    # FOR EACH DAY FIRST (total dollars on hand on that day), THEN
    # averaged over days. Averaging raw per-row values (skipping the
    # daily sum step) silently divides by the number of SKUs and wildly
    # overstates turnover -- this is the single easiest place to get
    # this KPI wrong in practice.
    daily_group_cols = cols + ["date"] if cols else ["date"]
    daily_inv = d.groupby(daily_group_cols)["inventory_value"].sum().reset_index()
    inv_agg = daily_inv.groupby(cols)["inventory_value"].mean().reset_index(name="avg_inventory_value") if cols else \
        pd.DataFrame([{"avg_inventory_value": daily_inv["inventory_value"].mean()}])

    agg = cogs_agg.merge(inv_agg, on=cols, how="left") if cols else pd.concat([cogs_agg, inv_agg], axis=1)
    agg["annualized_cogs"] = agg["total_cogs"] * (period_days / n_days)
    agg["inventory_turnover"] = (agg["annualized_cogs"] / agg["avg_inventory_value"]).round(2)
    return agg[[*cols, "avg_inventory_value", "annualized_cogs", "inventory_turnover"]] if cols else \
        agg[["avg_inventory_value", "annualized_cogs", "inventory_turnover"]]


def executive_insights(daily_ops: pd.DataFrame, purchase_orders: pd.DataFrame,
                        products: pd.DataFrame, suppliers: pd.DataFrame,
                        warehouses: pd.DataFrame, top_n: int = 3) -> list[dict]:
    """
    Turns the KPI tables into a short list of decision-ready findings --
    the level of detail a CEO or VP Ops actually wants, NOT a dump of
    every chart. Each finding pairs a headline number with a concrete,
    actionable recommendation.

    This is deliberately different from the other functions in this
    file: those compute a metric, this one computes a STORY. Every
    finding here answers "so what should we do about it", not just
    "what happened".

    Returns a list of dicts: {headline, detail, impact, recommendation}
    """
    findings = []

    # --- Finding 1: revenue concentration in a small number of suppliers ---
    d = daily_ops.merge(products[["product_id", "supplier_id", "unit_price", "category"]], on="product_id")
    d["lost_units"] = d["units_demanded"] - d["units_fulfilled"]
    d["lost_revenue"] = d["lost_units"] * d["unit_price"]

    by_supplier = d.groupby("supplier_id").agg(
        lost_units=("lost_units", "sum"), lost_revenue=("lost_revenue", "sum")
    ).reset_index().merge(suppliers[["supplier_id", "supplier_name", "region", "reliability_score"]],
                           on="supplier_id").sort_values("lost_revenue", ascending=False)

    total_lost_revenue = d["lost_revenue"].sum()
    top_n_df = by_supplier.head(top_n)
    top_n_share = top_n_df["lost_revenue"].sum() / total_lost_revenue if total_lost_revenue else 0
    names = ", ".join(top_n_df["supplier_name"].tolist())

    findings.append({
        "headline": f"{top_n} suppliers are responsible for {top_n_share*100:.0f}% of all lost sales revenue",
        "detail": f"{names} account for ${top_n_df['lost_revenue'].sum():,.0f} of the "
                  f"${total_lost_revenue:,.0f} in total revenue lost to stock-outs over the period.",
        "impact": f"${top_n_df['lost_revenue'].sum():,.0f} at risk",
        "recommendation": "Prioritize supplier renegotiation or dual-sourcing for these accounts first — "
                           "fixing them addresses the majority of the problem without a company-wide initiative.",
    })

    # --- Finding 2: worst-performing product category ---
    cat = order_fulfillment_rate(d, group_cols=["category"]).sort_values("fulfillment_rate")
    worst_cat = cat.iloc[0]
    best_cat = cat.iloc[-1]
    findings.append({
        "headline": f"\"{worst_cat['category']}\" has the lowest fulfillment rate at "
                    f"{worst_cat['fulfillment_rate']*100:.0f}%",
        "detail": f"Compare to \"{best_cat['category']}\" at {best_cat['fulfillment_rate']*100:.0f}%. "
                  f"A {(best_cat['fulfillment_rate']-worst_cat['fulfillment_rate'])*100:.0f} point gap between "
                  f"categories suggests a category-specific issue (demand volatility, reorder points, or "
                  f"supplier mix), not a company-wide capacity problem.",
        "impact": f"{(best_cat['fulfillment_rate']-worst_cat['fulfillment_rate'])*100:.0f} pt gap vs best category",
        "recommendation": f"Audit reorder points and lead times specifically for \"{worst_cat['category']}\" "
                           f"products before adjusting inventory policy company-wide.",
    })

    # --- Finding 3: worst on-time supplier worth a direct conversation ---
    sc = supplier_scorecard(purchase_orders, suppliers)
    if len(sc):
        worst = sc.iloc[0]
        findings.append({
            "headline": f"{worst['supplier_name']} delivers on time only {worst['on_time_rate']*100:.0f}% "
                        f"of the time",
            "detail": f"Average lead time is {worst['avg_lead_time_days']:.0f} days, running "
                      f"{worst['avg_delay_days']:.1f} days late on average across {int(worst['po_count'])} "
                      f"orders in the period.",
            "impact": f"{worst['on_time_rate']*100:.0f}% on-time rate",
            "recommendation": "Schedule a supplier performance review, or begin qualifying a backup "
                               "supplier in the same region as a hedge.",
        })

    # --- Finding 4: warehouse spread (is it a company-wide or localized issue) ---
    wh_fr = order_fulfillment_rate(d, group_cols=["warehouse_id"]).merge(warehouses, on="warehouse_id")
    spread = wh_fr["fulfillment_rate"].max() - wh_fr["fulfillment_rate"].min()
    if spread < 0.05:
        findings.append({
            "headline": "Fulfillment problems are consistent across all warehouses, not localized",
            "detail": f"Fulfillment rate varies by only {spread*100:.1f} points between the best and worst "
                      f"warehouse. This points to a sourcing/supplier problem rather than a "
                      f"warehouse-operations problem.",
            "impact": "Company-wide pattern",
            "recommendation": "Focus corrective action on supplier and category-level fixes (Findings 1-2) "
                               "rather than warehouse operations — the data doesn't support a warehouse-specific fix.",
        })
    else:
        worst_wh = wh_fr.sort_values("fulfillment_rate").iloc[0]
        findings.append({
            "headline": f"{worst_wh['warehouse_name']} underperforms other warehouses by "
                        f"{spread*100:.0f} points",
            "detail": f"Fulfillment rate at {worst_wh['warehouse_name']} is "
                      f"{worst_wh['fulfillment_rate']*100:.0f}%, meaningfully behind the network average.",
            "impact": f"{spread*100:.0f} pt gap vs best warehouse",
            "recommendation": f"Investigate {worst_wh['warehouse_name']}'s specific reorder policies and "
                               f"local supplier assignments — this looks like a localized, fixable issue.",
        })

    return findings


def supplier_scorecard(purchase_orders: pd.DataFrame, suppliers: pd.DataFrame) -> pd.DataFrame:
    """
    Combines lead time reliability with delay severity into a single
    supplier scorecard -- the kind of table a category manager would
    actually use in a quarterly business review with a supplier.
    """
    lt = average_lead_time(purchase_orders, group_cols=["supplier_id"])
    sc = lt.merge(suppliers[["supplier_id", "supplier_name", "region", "reliability_score"]],
                   on="supplier_id", how="left")
    sc = sc.sort_values("on_time_rate")
    return sc[["supplier_id", "supplier_name", "region", "po_count",
               "avg_lead_time_days", "avg_delay_days", "on_time_rate", "reliability_score"]]