# Sales Data Cleaning Challenge

**Run:** `pip install -r requirements.txt` → `python clean_data.py` → `streamlit run app.py`

| File | What it is |
|---|---|
| `sales_cleaned.csv` | Cleaned data (4,944 rows) incl. `revenue`, `price_imputed`, `discount_imputed` flags |
| `cleaning_log.csv` | Rows removed / cells changed per step, with the reason |
| `data_quality_summary.txt` | What was wrong with the raw file |
| `charts/` | Top 5 categories, monthly revenue, top 3 cities (each with title, axis labels, insight line) |
| `insights.md` | Numbers behind the charts + bonus comparison |
| `clean_data.py`, `app.py` | Reproducible pipeline and Streamlit dashboard (category filter + KPI row) |

## Problems found and decisions
- **120 exact duplicate rows** → removed.
- **41 city / 25 category spellings** (case, spaces, "Bangalore") → 8 cities, 5 categories.
- **3 date formats** (dd-mm-yyyy, dd-Mon-yy, mm-dd-yyyy) → ISO. Month-first dates with day ≤ 12 can't be told apart and were read as day-first (known limitation).
- **Quantity 0, -1, 500** (56 rows) → dropped; valid orders are 1-4 units.
- **Unit price 0 / 250,000 sentinels + 153 blanks** → product median (prices are tight per product), flagged.
- **Discount 150%** → 15% (decimal-shift typo); **blank discount** → 0, flagged.
- **Missing city / name** → recovered from the same customer_id's other orders; the rest "Unknown". **Missing payment** → "Unknown".

## Revenue definition
`revenue = quantity × unit_price × (1 − discount_pct/100)` is computed for every row. Headline analysis uses **Delivered orders only** (Cancelled/Returned aren't real revenue); the dashboard has a toggle for all orders.
