# Supply Chain Analytics Dashboard

An interactive dashboard analyzing shipping delays, warehouse efficiency,
inventory levels, and supplier performance for a simulated consumer
electronics distribution business — built with Python, pandas, and
Streamlit.

## Why simulated data (not just random numbers)

`generate_data.py` doesn't just fill columns with random values. It runs
a **day-by-day inventory simulation** across 2 years, ~5 warehouses, and
~20 products: demand is drawn each day, inventory decrements when orders
are fulfilled, purchase orders are triggered automatically when stock
hits the reorder point, and suppliers deliver late in proportion to a
"reliability score." That's what makes the KPIs internally consistent —
a supplier with a bad reliability score actually causes more stock-outs
downstream, the same way it would with real data.

## KPIs covered

| KPI | Business question it answers |
|---|---|
| **Order Fulfillment Rate** | Of everything customers wanted, how much did we actually ship? |
| **Inventory Turnover** | How efficiently is capital tied up in inventory being used? |
| **Lead Time** (+ delay vs. promised) | How long does replenishment really take, and how reliable is that? |
| **Stock-out Rate** | How often does demand outrun available inventory? |

See the docstrings in `analytics.py` for the full definitions and the
reasoning behind each calculation — that's the part worth reading if
you want the domain knowledge, not just the dashboard.

## Project structure

```
supply-chain-analytics/
├── generate_data.py    # simulates the dataset (run once)
├── analytics.py         # pandas functions computing each KPI
├── app.py                # Streamlit dashboard
├── requirements.txt
└── data/                  # generated CSVs (created by generate_data.py)
```

## Run it locally

```bash
pip install -r requirements.txt
python generate_data.py     # generates ./data/*.csv (~2-3 seconds)
streamlit run app.py         # opens the dashboard at localhost:8501
```

## Deploy it for free (to get a shareable link for LinkedIn)

1. Push this folder to a public GitHub repo.
2. Go to [share.streamlit.io](https://share.streamlit.io) (Streamlit
   Community Cloud), sign in with GitHub.
3. Click "New app," point it at your repo and `app.py`.
4. It'll auto-install `requirements.txt` and deploy. You'll get a live
   URL like `yourname-supply-chain-analytics.streamlit.app`.

**Note:** the deployed app needs `data/*.csv` to exist. Either commit the
generated CSVs to the repo, or add a small startup check in `app.py`
that runs `generate_data.py` if the `data/` folder is missing — happy to
add that if you want the repo to regenerate data automatically on deploy.

## Possible next steps (if you want to extend it further)

- Add a demand forecasting model (e.g. Prophet or a simple moving
  average) and compare forecast vs. actual
- Add a "safety stock calculator" that recommends reorder points based
  on lead time variance
- Swap the synthetic data for a real public dataset (e.g. a Kaggle
  logistics dataset) and compare how the KPIs change
