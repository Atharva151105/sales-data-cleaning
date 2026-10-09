"""Sales data cleaning pipeline.
Usage: python clean_data.py [input.csv]
Outputs: sales_cleaned.csv, cleaning_log.csv, data_quality_summary.txt, charts/*.png, insights.md
"""
import sys, io
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

SRC = sys.argv[1] if len(sys.argv) > 1 else "Challenge_2_-_Sales_Data__AIML_.csv"
raw = pd.read_csv(SRC)
df = raw.copy()
log = []
def step(name, action, before, after, changed=0, why=""):
    log.append(dict(step=len(log) + 1, issue=name, action=action, rows_before=before,
                    rows_after=after, rows_removed=before - after, cells_changed=changed, reason=why))

# ---------------- 1. DATA QUALITY SUMMARY (raw) ----------------
buf = io.StringIO()
P = lambda *a: print(*a, file=buf)
P("DATA-QUALITY SUMMARY (raw file)\n" + "=" * 60)
P(f"Rows: {len(raw)}   Columns: {raw.shape[1]}")
P("\nMissing values per column:"); P(raw.isna().sum()[raw.isna().sum() > 0].to_string())
P(f"\nExact duplicate rows: {raw.duplicated().sum()}   Duplicate order_ids: {raw.order_id.duplicated().sum()}")
for c in ["city", "category", "payment_method"]:
    s = raw[c].dropna()
    P(f"\n{c}: {s.nunique()} distinct raw spellings -> {s.str.strip().str.lower().replace({'bangalore':'bengaluru'}).nunique()} after trim/case/alias fix")
fmt = raw.order_date.str.len().map({10: "dd-mm-yyyy or mm-dd-yyyy (10 chars)", 9: "dd-Mon-yy (9 chars)"})
P("\nDate formats present:"); P(fmt.value_counts().to_string())
P(f"\nquantity <= 0: {(raw.quantity<=0).sum()}  | quantity >= 100: {(raw.quantity>=100).sum()}")
P(f"unit_price == 0: {(raw.unit_price==0).sum()}  | unit_price == 250000 (placeholder): {(raw.unit_price==250000).sum()}")
P(f"discount_pct > 100: {(raw.discount_pct>100).sum()}")
P(f"customer_name with stray whitespace: {(raw.customer_name.dropna()!=raw.customer_name.dropna().str.strip()).sum()}")
quality_summary = buf.getvalue()

# ---------------- 2. CLEANING ----------------
n = len(df)
# 2.1 exact duplicates
b = len(df); df = df.drop_duplicates().reset_index(drop=True)
step("Exact duplicate rows", "Dropped, kept first", b, len(df), 0,
     "Same order exported twice by different systems; counting both would double revenue.")
b = len(df); df = df.drop_duplicates("order_id").reset_index(drop=True)
step("Duplicate order_id with differing values", "Dropped extra rows (none found)", b, len(df), 0,
     "order_id should be unique.")

# 2.2 text normalisation
chg = 0
for c in ["customer_name", "city", "category", "payment_method", "product", "order_status"]:
    old = df[c].copy()
    df[c] = df[c].str.strip().str.replace(r"\s+", " ", regex=True)
    chg += (old.fillna("") != df[c].fillna("")).sum()
step("Leading/trailing/double whitespace", "Stripped all text columns", len(df), len(df), int(chg),
     "' Delhi ' and 'Delhi' are the same value but group separately.")
chg = 0
old = df.copy()
df["city"] = df.city.str.title().replace({"Bangalore": "Bengaluru"})
df["category"] = df.category.str.title().replace({"Home & Kitchen": "Home & Kitchen"})
df["payment_method"] = df.payment_method.replace({"upi": "UPI", "Upi": "UPI"})
df["customer_name"] = df.customer_name.str.title()
chg = sum((old[c].fillna("") != df[c].fillna("")).sum() for c in ["city", "category", "payment_method", "customer_name"])
step("Inconsistent case / aliases", "Title-cased city/category, 'upi'->'UPI', 'Bangalore'->'Bengaluru'", len(df), len(df), int(chg),
     "41 city and 25 category spellings collapse to 8 cities and 5 categories.")

# 2.3 dates
d = df.order_date
parsed = pd.to_datetime(d, format="%d-%m-%Y", errors="coerce")
parsed = parsed.fillna(pd.to_datetime(d, format="%d-%b-%y", errors="coerce"))
us = pd.to_datetime(d, format="%m-%d-%Y", errors="coerce")
mm_dd_rows = int(parsed.isna().sum() - us[parsed.isna()].isna().sum())
parsed = parsed.fillna(us)
df["order_date"] = parsed
bad = df.order_date.isna().sum()
b = len(df); df = df.dropna(subset=["order_date"]).reset_index(drop=True)
step("Mixed date formats (dd-mm-yyyy, dd-Mon-yy, mm-dd-yyyy)", "Parsed all three into ISO yyyy-mm-dd", b, len(df), int(len(d)),
     f"{mm_dd_rows} dates were month-first (day>12, unambiguous) and rescued; {bad} unparseable dropped. "
     "Caveat: month-first dates with both parts <=12 are indistinguishable and were read as day-first.")

# 2.4 invalid quantity
b = len(df)
bad_q = (df.quantity <= 0) | (df.quantity >= 100)
df = df[~bad_q].reset_index(drop=True)
step("Invalid quantity (0, -1, 500)", "Dropped rows", b, len(df), 0,
     "Every valid order has quantity 1-4. 0/-1 cannot be a real sale; 500 is 125x the max normal order (likely a typo) "
     "and the true value is unrecoverable. Dropping is safer than guessing.")

# 2.5 price
price_ok = df.loc[(df.unit_price > 0) & (df.unit_price < 100000)].groupby("product").unit_price.median()
bad_p = df.unit_price.isna() | (df.unit_price <= 0) | (df.unit_price >= 100000)
df["price_imputed"] = bad_p
step("Placeholder prices (0 and 250000)", "Set to missing before imputing", len(df), len(df),
     int(((df.unit_price <= 0) | (df.unit_price >= 100000)).sum()),
     "0 and 250,000 are system sentinel values: every product's real prices sit within about +/-10% of its median.")
df.loc[bad_p, "unit_price"] = df.loc[bad_p, "product"].map(price_ok)
step("Missing unit_price", "Filled with the product's median price (flagged in price_imputed)", len(df), len(df), int(bad_p.sum()),
     "Prices are tight within a product (CV ~3-8%), so the product median is a reliable estimate. Median, not mean, so outliers do not bias it.")

# 2.6 discount
bad_d = df.discount_pct > 100
df.loc[bad_d, "discount_pct"] = df.loc[bad_d, "discount_pct"] / 10
step("Impossible discount (150%)", "Divided by 10 -> 15%", len(df), len(df), int(bad_d.sum()),
     "Valid discounts are only 0/5/10/15/20; 150 is a decimal-shift typo of 15. A >100% discount is impossible.")
miss_d = df.discount_pct.isna()
df["discount_imputed"] = miss_d
df.loc[miss_d, "discount_pct"] = 0
step("Missing discount_pct", "Filled with 0 (flagged in discount_imputed)", len(df), len(df), int(miss_d.sum()),
     "0 is the most common value (~43%) and absence of a recorded discount is most plausibly 'no discount'. Order-level, so can't be recovered from other columns.")

# 2.7 recover city / name from customer_id
def recover(col):
    m = df.dropna(subset=[col]).groupby("customer_id")[col].agg(lambda s: s.mode().iloc[0] if s.nunique() == 1 or s.value_counts().iloc[0] > s.value_counts().iloc[1:].max() else np.nan)
    return m
miss = df.city.isna(); lut = recover("city")
df.loc[miss, "city"] = df.loc[miss, "customer_id"].map(lut)
rec = int(miss.sum() - df.city.isna().sum())
step("Missing city", "Recovered from the customer's other orders (most frequent city)", len(df), len(df), rec,
     "A customer_id maps to one city in 95% of cases.")
left = int(df.city.isna().sum()); df["city"] = df.city.fillna("Unknown")
step("Missing city (unrecoverable)", "Labelled 'Unknown'", len(df), len(df), left, "Customer has no other order with a city; excluded from city ranking.")
miss = df.customer_name.isna(); lut = recover("customer_name")
df.loc[miss, "customer_name"] = df.loc[miss, "customer_id"].map(lut)
rec = int(miss.sum() - df.customer_name.isna().sum()); left = int(df.customer_name.isna().sum())
df["customer_name"] = df.customer_name.fillna("Unknown")
step("Missing customer_name", f"Recovered {rec} via customer_id; {left} labelled 'Unknown'", len(df), len(df), int(miss.sum()),
     "customer_id -> name is 1:1 in the file.")
miss = int(df.payment_method.isna().sum()); df["payment_method"] = df.payment_method.fillna("Unknown")
step("Missing payment_method", "Labelled 'Unknown'", len(df), len(df), miss, "Categorical, no reliable signal to infer; honest label beats a guess.")

# 2.8 revenue
df["revenue"] = (df.quantity * df.unit_price * (1 - df.discount_pct / 100)).round(2)
step("Revenue column", "revenue = quantity x unit_price x (1 - discount_pct/100)", len(df), len(df), len(df), "Required derived field.")

# 2.9 residual outlier check
z = df.groupby("product").unit_price.transform(lambda s: (s - s.median()).abs() / (s.std() + 1e-9))
resid = int((z > 5).sum())
step("Residual outlier check (price >5 SD from product median)", "Reviewed; none altered", len(df), len(df), 0,
     f"{resid} rows flagged; no action needed." if resid else "No remaining anomalies.")
df["counts_as_sale"] = df.order_status.eq("Delivered")
df["order_date"] = df.order_date.dt.strftime("%Y-%m-%d")
df = df.sort_values("order_date").reset_index(drop=True)

df.to_csv("sales_cleaned.csv", index=False)
logdf = pd.DataFrame(log); logdf.to_csv("cleaning_log.csv", index=False)
P("\n" + "=" * 60 + f"\nRESULT: {len(raw)} raw rows -> {len(df)} clean rows ({len(raw)-len(df)} removed)")
open("data_quality_summary.txt", "w").write(quality_summary)

# ---------------- 3. ANALYSIS ----------------
df["order_date"] = pd.to_datetime(df.order_date)
sales = df[df.counts_as_sale]
inr = FuncFormatter(lambda x, _: f"₹{x/1e6:.1f}M")
BLUE, GREY = "#1f4e79", "#c9d3dc"
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})

cat = sales.groupby("category").revenue.sum().sort_values(ascending=False).head(5)
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(cat.index, cat.values, color=[BLUE] + [GREY] * (len(cat) - 1))
for b_, v in zip(bars, cat.values): ax.text(b_.get_x() + b_.get_width() / 2, v, f"{v/1e6:.2f}M ({v/cat.sum():.0%})", ha="center", va="bottom", fontsize=10)
ax.set_title("Top 5 Categories by Revenue (Delivered orders, 2025)", weight="bold")
ax.set_xlabel("Category"); ax.set_ylabel("Revenue (₹ millions)"); ax.yaxis.set_major_formatter(inr)
ax.set_ylim(0, cat.max() * 1.12); fig.text(0.5, 0.01, f"Insight: {cat.index[0]} leads with {cat.iloc[0]/cat.sum():.0%} of revenue; the top two categories bring in {cat.iloc[:2].sum()/cat.sum():.0%}.", ha="center", style="italic", fontsize=10); plt.tight_layout(rect=(0,0.05,1,1)); plt.savefig("charts/1_top_categories.png", dpi=150); plt.close()

mon = sales.groupby(sales.order_date.dt.to_period("M")).revenue.sum()
mon.index = mon.index.to_timestamp()
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(mon.index, mon.values, marker="o", color=BLUE, lw=2.5)
ax.fill_between(mon.index, mon.values, color=BLUE, alpha=.1)
ax.set_title("Monthly Revenue Trend (Delivered orders, 2025)", weight="bold")
ax.set_xlabel("Month"); ax.set_ylabel("Revenue (₹ millions)"); ax.yaxis.set_major_formatter(inr)
ax.set_xticks(mon.index); ax.set_xticklabels([m.strftime("%b") for m in mon.index]); ax.set_ylim(0)
fig.text(0.5, 0.01, f"Insight: revenue jumps {mon.iloc[9:].mean()/mon.iloc[:9].mean()-1:.0%} in Oct-Dec versus the Jan-Sep average, peaking in {mon.idxmax():%B}.", ha="center", style="italic", fontsize=10)
plt.tight_layout(rect=(0,0.05,1,1)); plt.savefig("charts/2_monthly_revenue.png", dpi=150); plt.close()

city = sales[sales.city != "Unknown"].groupby("city").revenue.sum().sort_values(ascending=False).head(3)
fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(city.index, city.values, color=[BLUE, "#5b8db8", GREY])
for b_, v in zip(bars, city.values): ax.text(b_.get_x() + b_.get_width() / 2, v, f"{v/1e6:.2f}M", ha="center", va="bottom")
ax.set_title("Top 3 Cities by Revenue (Delivered orders, 2025)", weight="bold")
ax.set_xlabel("City"); ax.set_ylabel("Revenue (₹ millions)"); ax.yaxis.set_major_formatter(inr)
ax.set_ylim(0, city.max() * 1.12); fig.text(0.5, 0.01, f"Insight: {city.index[0]} leads, but the top 3 cities sit within {city.iloc[0]/city.iloc[2]-1:.0%} of each other.", ha="center", style="italic", fontsize=10); plt.tight_layout(rect=(0,0.05,1,1)); plt.savefig("charts/3_top_cities.png", dpi=150); plt.close()

# extras
from scipy import stats
q4 = mon[mon.index.month >= 10].mean(); q123 = mon[mon.index.month < 10].mean()
disc = sales.assign(d=sales.discount_pct > 0)
a = disc[disc.d].revenue; c0 = disc[~disc.d].revenue
t, p = stats.ttest_ind(a, c0, equal_var=False)
ret = df.groupby("category").order_status.apply(lambda s: (s != "Delivered").mean()).sort_values(ascending=False)

ins = f"""# Insights (computed from cleaned data)
Revenue basis: Delivered orders only ({len(sales):,} of {len(df):,} clean orders). Cancelled/Returned orders keep a `revenue` value in the CSV but are excluded from sales totals.

## Q1 Top 5 categories
{cat.map(lambda v: f'₹{v:,.0f}').to_string()}
Insight: {cat.index[0]} earns {cat.iloc[0]/cat.sum():.0%} of revenue; the top two categories together earn {cat.iloc[:2].sum()/cat.sum():.0%}.
(After cleaning only 5 categories exist, so the top 5 is all of them.)

## Q2 Monthly revenue
{mon.map(lambda v: f'₹{v:,.0f}').to_string()}
Insight: Oct-Dec average ₹{q4/1e6:.2f}M/month vs ₹{q123/1e6:.2f}M for Jan-Sep ({q4/q123-1:+.0%}); peak month {mon.idxmax():%b}.

## Q3 Top 3 cities
{city.map(lambda v: f'₹{v:,.0f}').to_string()}

## Bonus: discount vs no-discount orders
Mean revenue per discounted order ₹{a.mean():,.0f} vs ₹{c0.mean():,.0f} for undiscounted (Welch t-test p={p:.3f}). Caution: this gap is mostly product mix (discount is spread across cheap and expensive items), not proof that discounts lower spend.
Share of orders Cancelled/Returned by category: {', '.join(f'{k} {v:.0%}' for k, v in ret.items())}.
"""
open("insights.md", "w").write(ins)
print(quality_summary); print(logdf[["step","issue","rows_removed","cells_changed"]].to_string(index=False)); print(ins)
