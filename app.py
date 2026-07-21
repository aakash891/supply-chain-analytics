
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from analytics import (
    order_fulfillment_rate, stockout_rate, average_lead_time,
    inventory_turnover, supplier_scorecard, executive_insights
)

st.set_page_config(page_title="Ops Insights Dashboard", layout="wide", page_icon="📦")

# =======================================================================
# DESIGN TOKENS
# A small, deliberate palette: deep slate-navy for structure/text, a
# single blue accent for primary data, and semantic colors (teal/amber/
# red) reserved ONLY for good/caution/risk signals -- never decoration.
# =======================================================================
NAVY = "#0F172A"
NAVY_SOFT = "#1E293B"
SLATE = "#64748B"
SLATE_LIGHT = "#94A3B8"
BORDER = "#E2E8F0"
BG = "#F8FAFC"
CARD = "#FFFFFF"
ACCENT = "#2563EB"
ACCENT_SOFT = "#EFF6FF"
TEAL = "#0D9488"
TEAL_SOFT = "#F0FDFA"
AMBER = "#D97706"
AMBER_SOFT = "#FFFBEB"
RED = "#DC2626"
RED_SOFT = "#FEF2F2"

CHART_COLORWAY = [ACCENT, TEAL, AMBER, "#7C3AED", RED, SLATE]

PLOTLY_LAYOUT = dict(
    font=dict(family="Inter, -apple-system, sans-serif", color=NAVY, size=13),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    colorway=CHART_COLORWAY,
    margin=dict(l=10, r=10, t=10, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=12)),
    xaxis=dict(gridcolor=BORDER, zeroline=False, linecolor=BORDER),
    yaxis=dict(gridcolor=BORDER, zeroline=False, linecolor=BORDER),
)

def style_fig(fig, height=320):
    fig.update_layout(**PLOTLY_LAYOUT, height=height)
    fig.update_xaxes(gridcolor=BORDER, zeroline=False, linecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, zeroline=False, linecolor=BORDER)
    return fig

# =======================================================================
# GLOBAL CSS
# =======================================================================
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, sans-serif;
}}
.stApp {{
    background-color: {BG};
}}
#MainMenu, footer, header {{visibility: hidden;}}
.block-container {{
    padding-top: 1.5rem;
    max-width: 1200px;
}}

/* ---- Top banner ---- */
.dash-header {{
    background: linear-gradient(135deg, {NAVY} 0%, {NAVY_SOFT} 100%);
    border-radius: 14px;
    padding: 28px 32px;
    margin-bottom: 24px;
}}
.dash-header .eyebrow {{
    color: {SLATE_LIGHT};
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 6px;
}}
.dash-header h1 {{
    color: #FFFFFF;
    font-size: 26px;
    font-weight: 700;
    margin: 0 0 6px 0;
}}
.dash-header p {{
    color: {SLATE_LIGHT};
    font-size: 14px;
    margin: 0;
    max-width: 720px;
    line-height: 1.5;
}}

/* ---- KPI cards ---- */
.kpi-row {{ display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }}
.kpi-card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 18px 20px;
    flex: 1 1 220px;
    min-width: 220px;
    border-top: 3px solid var(--accent, {ACCENT});
}}
.kpi-label {{
    color: {SLATE};
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    margin-bottom: 8px;
}}
.kpi-value {{
    color: {NAVY};
    font-size: 28px;
    font-weight: 700;
    line-height: 1;
    margin-bottom: 6px;
}}
.kpi-delta {{
    font-size: 12.5px;
    font-weight: 500;
}}
.kpi-delta.good {{ color: {TEAL}; }}
.kpi-delta.bad {{ color: {RED}; }}
.kpi-delta.neutral {{ color: {SLATE}; }}

/* ---- Section headers ---- */
.section-title {{
    color: {NAVY};
    font-size: 16px;
    font-weight: 600;
    margin: 4px 0 14px 0;
}}
.section-sub {{
    color: {SLATE};
    font-size: 13px;
    margin: -10px 0 18px 0;
}}

/* ---- Insight cards ---- */
.insight-card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-left: 4px solid {ACCENT};
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 14px;
}}
.insight-card.risk {{ border-left-color: {RED}; }}
.insight-card.caution {{ border-left-color: {AMBER}; }}
.insight-card.neutral {{ border-left-color: {SLATE}; }}
.insight-top {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }}
.insight-num {{
    display: inline-block;
    color: {SLATE};
    font-size: 12px;
    font-weight: 700;
    margin-bottom: 4px;
    letter-spacing: 0.04em;
}}
.insight-headline {{
    color: {NAVY};
    font-size: 15.5px;
    font-weight: 600;
    margin: 0 0 8px 0;
    line-height: 1.4;
}}
.insight-detail {{
    color: {SLATE};
    font-size: 13.5px;
    line-height: 1.6;
    margin: 0 0 10px 0;
}}
.insight-badge {{
    background: {ACCENT_SOFT};
    color: {ACCENT};
    font-size: 13px;
    font-weight: 700;
    padding: 6px 14px;
    border-radius: 8px;
    white-space: nowrap;
}}
.insight-card.risk .insight-badge {{ background: {RED_SOFT}; color: {RED}; }}
.insight-card.caution .insight-badge {{ background: {AMBER_SOFT}; color: {AMBER}; }}
.insight-rec {{
    font-size: 13.5px;
    color: {NAVY};
    background: {BG};
    border-radius: 8px;
    padding: 10px 14px;
    margin-top: 4px;
}}
.insight-rec b {{ color: {ACCENT}; }}

/* ---- Tabs: pill-style segmented control, not default underline tabs ---- */
.stTabs [data-baseweb="tab-list"] {{
    gap: 6px;
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 6px;
    margin-bottom: 20px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    flex-wrap: nowrap;
}}
.stTabs [data-baseweb="tab"] {{
    height: 40px;
    color: {SLATE};
    font-weight: 500;
    font-size: 13.5px;
    border-radius: 8px;
    padding: 0 18px;
    background: transparent;
    transition: background 0.15s ease, color 0.15s ease;
}}
.stTabs [data-baseweb="tab"]:hover {{
    background: {BG};
    color: {NAVY};
}}
.stTabs [aria-selected="true"] {{
    color: #FFFFFF !important;
    font-weight: 600;
    background: {NAVY} !important;
}}
.stTabs [aria-selected="true"]:hover {{
    background: {NAVY} !important;
}}
.stTabs [data-baseweb="tab-highlight"] {{
    display: none;
}}
.stTabs [data-baseweb="tab-border"] {{
    display: none;
}}
.stTabs [data-baseweb="tab-panel"] {{
    padding-top: 4px;
}}

/* ---- Sidebar ---- */
[data-testid="stSidebar"] {{
    background: {NAVY};
}}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] h3 {{
    color: #E2E8F0 !important;
}}
[data-testid="stSidebar"] .stSelectbox label, [data-testid="stSidebar"] .stDateInput label {{
    font-size: 12.5px;
    font-weight: 600;
    color: {SLATE_LIGHT} !important;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}}
/* Input boxes (selectbox, date input) need their own dark background --
   without this, text stays light-on-light-default-white and disappears. */
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="base-input"],
[data-testid="stSidebar"] input {{
    background-color: {NAVY_SOFT} !important;
    border-color: #334155 !important;
    color: #F1F5F9 !important;
}}
[data-testid="stSidebar"] [data-baseweb="select"] span,
[data-testid="stSidebar"] [data-baseweb="select"] div {{
    color: #F1F5F9 !important;
}}
[data-testid="stSidebar"] svg {{
    fill: #94A3B8 !important;
}}
/* Dropdown menu popover renders outside the sidebar DOM node, in a portal --
   style it globally so it isn't caught by the sidebar-only selectors above. */
[data-baseweb="popover"] [data-baseweb="menu"] {{
    background-color: {NAVY_SOFT} !important;
}}
[data-baseweb="popover"] [data-baseweb="menu"] li {{
    color: #F1F5F9 !important;
}}
[data-baseweb="popover"] [data-baseweb="menu"] li:hover {{
    background-color: {NAVY} !important;
}}

/* ---- Dataframe / misc ---- */
[data-testid="stDataFrame"] {{ border-radius: 10px; overflow: hidden; border: 1px solid {BORDER}; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius: 12px !important; border-color: {BORDER} !important; }}
</style>
""", unsafe_allow_html=True)


def kpi_card(label, value, delta=None, delta_tone="neutral", accent=ACCENT):
    delta_html = f'<div class="kpi-delta {delta_tone}">{delta}</div>' if delta else ""
    st.markdown(f"""
    <div class="kpi-card" style="--accent:{accent}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------
@st.cache_data
def load_data():
    daily_ops = pd.read_csv("data/daily_ops.csv", parse_dates=["date"])
    purchase_orders = pd.read_csv("data/purchase_orders.csv",
                                   parse_dates=["order_date", "promised_delivery_date", "actual_delivery_date"])
    products = pd.read_csv("data/products.csv")
    suppliers = pd.read_csv("data/suppliers.csv")
    warehouses = pd.read_csv("data/warehouses.csv")
    return daily_ops, purchase_orders, products, suppliers, warehouses

daily_ops, purchase_orders, products, suppliers, warehouses = load_data()

# ---------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------
st.sidebar.markdown("### Filters")

date_min, date_max = daily_ops["date"].min(), daily_ops["date"].max()
date_range = st.sidebar.date_input("Date range", (date_min, date_max),
                                    min_value=date_min, max_value=date_max)
if len(date_range) == 2:
    start_date, end_date = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
else:
    start_date, end_date = date_min, date_max

wh_options = ["All"] + sorted(warehouses["warehouse_id"].unique().tolist())
selected_wh = st.sidebar.selectbox("Warehouse", wh_options)

cat_options = ["All"] + sorted(products["category"].unique().tolist())
selected_cat = st.sidebar.selectbox("Product category", cat_options)

# ---------------------------------------------------------------------
# Apply filters
# ---------------------------------------------------------------------
d = daily_ops[(daily_ops["date"] >= start_date) & (daily_ops["date"] <= end_date)]
po = purchase_orders[(purchase_orders["order_date"] >= start_date) & (purchase_orders["order_date"] <= end_date)]

if selected_wh != "All":
    d = d[d["warehouse_id"] == selected_wh]
    po = po[po["warehouse_id"] == selected_wh]

if selected_cat != "All":
    cat_products = products[products["category"] == selected_cat]["product_id"]
    d = d[d["product_id"].isin(cat_products)]
    po = po[po["product_id"].isin(cat_products)]

# ---------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------
st.markdown(f"""
<div class="dash-header">
    <div class="eyebrow">Consumer Electronics Distribution </div>
    <h1>Ops Insights Dashboard</h1>
    <p>Shipping delays, warehouse efficiency, inventory levels, and supplier performance across
    {len(warehouses)} warehouses and {len(products)} products, {date_min.strftime('%b %Y')}&ndash;{date_max.strftime('%b %Y')}.</p>
</div>
""", unsafe_allow_html=True)

if d.empty:
    st.warning("No data for the selected filters.")
    st.stop()

# ---------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------
fr = order_fulfillment_rate(d)
sr = stockout_rate(d)
lt = average_lead_time(po) if len(po) else None
turnover = inventory_turnover(d, products)

fr_val = fr['fulfillment_rate'].iloc[0]
sr_val = sr['stockout_rate'].iloc[0]

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi_card("Order Fulfillment Rate", f"{fr_val*100:.1f}%",
              "Target: 95%+", "good" if fr_val >= 0.9 else "bad", ACCENT)
with c2:
    kpi_card("Inventory Turnover", f"{turnover['inventory_turnover'].iloc[0]:.1f}x",
              "Annualized", "neutral", TEAL)
with c3:
    if lt is not None:
        delay = lt['avg_delay_days'].iloc[0]
        kpi_card("Avg Lead Time", f"{lt['avg_lead_time_days'].iloc[0]:.0f} days",
                  f"{delay:+.1f} vs promised", "bad" if delay > 0 else "good", AMBER)
    else:
        kpi_card("Avg Lead Time", "n/a", None)
with c4:
    kpi_card("Stock-out Rate", f"{sr_val*100:.1f}%",
              "of warehouse-product-days", "bad" if sr_val > 0.05 else "good", RED)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------
tab0, tab1, tab2, tab3, tab4 = st.tabs(
    ["Executive Insights", "Trends", "Warehouse Efficiency", "Supplier Performance", "Data"]
)

with tab0:
    st.markdown('<div class="section-title">What leadership should know</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Auto-generated from the current filter selection &mdash; ranked by business impact, with a recommended next step for each.</div>', unsafe_allow_html=True)

    findings = executive_insights(d, po, products, suppliers, warehouses)

    if not findings:
        st.info("Not enough data in the selected filters to generate findings.")
    else:
        tone_cycle = ["risk", "caution", "neutral", "neutral"]
        for i, f in enumerate(findings):
            tone = tone_cycle[i % len(tone_cycle)]
            st.markdown(f"""
            <div class="insight-card {tone}">
                <div class="insight-top">
                    <div>
                        <div class="insight-num">FINDING {i+1}</div>
                        <div class="insight-headline">{f['headline']}</div>
                    </div>
                    <div class="insight-badge">{f['impact']}</div>
                </div>
                <p class="insight-detail">{f['detail']}</p>
                <div class="insight-rec"><b>Recommendation</b> &nbsp;{f['recommendation']}</div>
            </div>
            """, unsafe_allow_html=True)

with tab1:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-title">Daily fulfillment rate</div>', unsafe_allow_html=True)
        trend = d.groupby("date")[["units_demanded", "units_fulfilled"]].sum().reset_index()
        trend["fulfillment_rate"] = (trend["units_fulfilled"] / trend["units_demanded"] * 100).round(1)
        fig = px.line(trend, x="date", y="fulfillment_rate", labels={"fulfillment_rate": "Fulfillment rate (%)", "date": ""})
        fig.update_traces(line_color=ACCENT, line_width=2)
        st.plotly_chart(style_fig(fig, 320), use_container_width=True, config={"displayModeBar": False})

    with col2:
        st.markdown('<div class="section-title">Units demanded vs. fulfilled</div>', unsafe_allow_html=True)
        fig2 = px.line(trend, x="date", y=["units_demanded", "units_fulfilled"], labels={"value": "Units", "date": "", "variable": ""})
        fig2.update_traces(line_width=2)
        for tr, color in zip(fig2.data, [SLATE_LIGHT, ACCENT]):
            tr.line.color = color
        st.plotly_chart(style_fig(fig2, 320), use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="section-title">Stock-out rate by month</div>', unsafe_allow_html=True)
    monthly = d.copy()
    monthly["month"] = monthly["date"].dt.to_period("M").astype(str)
    monthly_so = monthly.groupby("month")["stockout_flag"].mean().reset_index()
    monthly_so["stockout_flag"] = (monthly_so["stockout_flag"] * 100).round(1)
    fig3 = px.bar(monthly_so, x="month", y="stockout_flag", labels={"stockout_flag": "Stock-out rate (%)", "month": ""})
    fig3.update_traces(marker_color=AMBER)
    st.plotly_chart(style_fig(fig3, 280), use_container_width=True, config={"displayModeBar": False})

with tab2:
    st.markdown('<div class="section-title">Fulfillment rate by warehouse</div>', unsafe_allow_html=True)
    wh_fr = order_fulfillment_rate(d, group_cols=["warehouse_id"])
    wh_fr = wh_fr.merge(warehouses, on="warehouse_id")
    fig4 = px.bar(wh_fr.sort_values("fulfillment_rate"), x="fulfillment_rate", y="warehouse_name",
                  orientation="h", labels={"fulfillment_rate": "Fulfillment rate", "warehouse_name": ""})
    fig4.update_traces(marker_color=ACCENT)
    fig4.update_xaxes(tickformat=".0%")
    st.plotly_chart(style_fig(fig4, 280), use_container_width=True, config={"displayModeBar": False})

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-title">Inventory turnover by warehouse</div>', unsafe_allow_html=True)
        wh_turn = inventory_turnover(d, products, group_cols=["warehouse_id"]).merge(warehouses, on="warehouse_id")
        fig5 = px.bar(wh_turn.sort_values("inventory_turnover"), x="inventory_turnover", y="warehouse_name",
                      orientation="h", labels={"inventory_turnover": "Turnover (x/yr)", "warehouse_name": ""})
        fig5.update_traces(marker_color=TEAL)
        st.plotly_chart(style_fig(fig5, 280), use_container_width=True, config={"displayModeBar": False})

    with col2:
        st.markdown('<div class="section-title">Stock-out rate by warehouse</div>', unsafe_allow_html=True)
        wh_so = stockout_rate(d, group_cols=["warehouse_id"]).merge(warehouses, on="warehouse_id")
        fig6 = px.bar(wh_so.sort_values("stockout_rate"), x="stockout_rate", y="warehouse_name",
                      orientation="h", labels={"stockout_rate": "Stock-out rate", "warehouse_name": ""})
        fig6.update_traces(marker_color=RED)
        fig6.update_xaxes(tickformat=".0%")
        st.plotly_chart(style_fig(fig6, 280), use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="section-title">Fulfillment rate by product category</div>', unsafe_allow_html=True)
    cat_fr = d.merge(products[["product_id", "category"]], on="product_id")
    cat_fr = order_fulfillment_rate(cat_fr, group_cols=["category"])
    fig7 = px.bar(cat_fr.sort_values("fulfillment_rate"), x="fulfillment_rate", y="category",
                  orientation="h", labels={"fulfillment_rate": "Fulfillment rate", "category": ""})
    fig7.update_traces(marker_color=ACCENT)
    fig7.update_xaxes(tickformat=".0%")
    st.plotly_chart(style_fig(fig7, 280), use_container_width=True, config={"displayModeBar": False})

with tab3:
    st.markdown('<div class="section-title">Supplier scorecard</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Sorted by on-time delivery rate (worst first) &mdash; the suppliers most worth a conversation.</div>', unsafe_allow_html=True)
    scorecard = supplier_scorecard(po, suppliers) if len(po) else pd.DataFrame()
    if not scorecard.empty:
        display = scorecard.copy()
        display["on_time_rate"] = (display["on_time_rate"] * 100).round(0).astype(str) + "%"
        display["reliability_score"] = (display["reliability_score"] * 100).round(0).astype(str) + "%"
        st.dataframe(
            display.rename(columns={
                "supplier_name": "Supplier", "region": "Region", "po_count": "# POs",
                "avg_lead_time_days": "Avg lead time (days)", "avg_delay_days": "Avg delay (days)",
                "on_time_rate": "On-time rate", "reliability_score": "Reliability score"
            }).drop(columns=["supplier_id"]),
            use_container_width=True, hide_index=True
        )

        st.markdown('<div class="section-title" style="margin-top:24px">Lead time vs. delay by supplier region</div>', unsafe_allow_html=True)
        region_lt = average_lead_time(po.merge(suppliers[["supplier_id", "region"]], on="supplier_id"),
                                       group_cols=["region"])
        fig8 = px.scatter(region_lt, x="avg_lead_time_days", y="avg_delay_days", size="po_count",
                           text="region", labels={"avg_lead_time_days": "Avg lead time (days)",
                                                   "avg_delay_days": "Avg delay vs promised (days)"})
        fig8.update_traces(textposition="top center", marker=dict(color=ACCENT, line=dict(width=1, color="white")))
        st.plotly_chart(style_fig(fig8, 360), use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("No purchase orders in the selected filter range.")

with tab4:
    st.markdown('<div class="section-title">Underlying tables</div>', unsafe_allow_html=True)
    which = st.selectbox("Table", ["daily_ops", "purchase_orders", "products", "suppliers", "warehouses"])
    table_map = {
        "daily_ops": d, "purchase_orders": po, "products": products,
        "suppliers": suppliers, "warehouses": warehouses
    }
    st.dataframe(table_map[which], use_container_width=True, height=400)
    st.download_button(
        f"Download {which}.csv",
        table_map[which].to_csv(index=False).encode("utf-8"),
        file_name=f"{which}.csv", mime="text/csv"
    )
