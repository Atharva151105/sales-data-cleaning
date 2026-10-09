"""Run: streamlit run app.py   (needs sales_cleaned.csv in same folder)"""
import pandas as pd, streamlit as st
import plotly.express as px

st.set_page_config(page_title="Sales Dashboard", layout="wide")
@st.cache_data
def load():
    d = pd.read_csv("sales_cleaned.csv", parse_dates=["order_date"])
    return d
df = load()

st.title("E-commerce Sales Dashboard (2025)")
cats = st.sidebar.multiselect("Category", sorted(df.category.unique()), default=sorted(df.category.unique()))
status = st.sidebar.radio("Order basis", ["Delivered only", "All orders"])
f = df[df.category.isin(cats)]
if status == "Delivered only":
    f = f[f.order_status == "Delivered"]

orders = f.order_id.nunique(); rev = f.revenue.sum()
k1, k2, k3 = st.columns(3)
k1.metric("Total revenue", f"₹{rev:,.0f}")
k2.metric("Orders", f"{orders:,}")
k3.metric("Average order value", f"₹{rev / orders:,.0f}" if orders else "—")

c1, c2 = st.columns(2)
cat = f.groupby("category", as_index=False).revenue.sum().sort_values("revenue", ascending=False)
c1.plotly_chart(px.bar(cat, x="category", y="revenue", title="Revenue by category",
                       labels={"category": "Category", "revenue": "Revenue (₹)"}), use_container_width=True)
mon = f.groupby(f.order_date.dt.to_period("M").dt.to_timestamp(), as_index=False).revenue.sum()
c2.plotly_chart(px.line(mon, x="order_date", y="revenue", markers=True, title="Monthly revenue",
                        labels={"order_date": "Month", "revenue": "Revenue (₹)"}), use_container_width=True)
city = f[f.city != "Unknown"].groupby("city", as_index=False).revenue.sum().nlargest(3, "revenue")
st.plotly_chart(px.bar(city, x="city", y="revenue", title="Top 3 cities by revenue",
                       labels={"city": "City", "revenue": "Revenue (₹)"}), use_container_width=True)
with st.expander("Cleaning log"):
    st.dataframe(pd.read_csv("cleaning_log.csv"))
