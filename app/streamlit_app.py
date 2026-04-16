"""
Streamlit frontend for the CSV-to-JSON API.
Displays the Commodities dataset with search, filtering, and pagination.
"""

import streamlit as st
import requests
import pandas as pd

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Trade Data Explorer", layout="wide")
st.title("🌍 Trade Data Explorer")


@st.cache_data(ttl=60)
def fetch_datasets():
    """Fetch available datasets from the API root."""
    try:
        resp = requests.get(f"{API_BASE}/", timeout=5)
        resp.raise_for_status()
        return resp.json().get("datasets", {})
    except requests.RequestException as e:
        st.error(f"Could not connect to API at {API_BASE}: {e}")
        return {}


@st.cache_data(ttl=60)
def fetch_commodities(limit: int, offset: int, filters: dict):
    """Fetch commodities from the API with pagination and filters."""
    params = {"_limit": limit, "_offset": offset}
    params.update({k: v for k, v in filters.items() if v})
    try:
        resp = requests.get(f"{API_BASE}/api/commodities", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"API request failed: {e}")
        return {"total": 0, "data": [], "limit": limit, "offset": offset, "count": 0}


# ── Sidebar: API info ──────────────────────────────────────────────────────
datasets = fetch_datasets()

with st.sidebar:
    st.header("Available APIs")
    if datasets:
        for name, info in datasets.items():
            icon = "📦" if name == "commodities" else "📄"
            st.markdown(f"{icon} **{name.replace('_', ' ').title()}** — {info['records']:,} records")
    else:
        st.warning("No datasets available. Is the API running?")

    st.divider()
    st.caption(f"API: `{API_BASE}`")

# ── Main content: Commodities ──────────────────────────────────────────────
st.header("📦 Commodities")

# Filters
col1, col2, col3 = st.columns(3)
with col1:
    search_desc = st.text_input("Search description", placeholder="e.g. horses, bovine")
with col2:
    filter_declarable = st.selectbox("Declarable", ["All", "TRUE", "FALSE"])
with col3:
    filter_leaf = st.selectbox("Leaf", ["All", "TRUE", "FALSE"])

# Pagination controls
col_pg1, col_pg2, _ = st.columns([1, 1, 3])
with col_pg1:
    page_size = st.selectbox("Rows per page", [25, 50, 100, 250, 500], index=2)
with col_pg2:
    page_num = st.number_input("Page", min_value=1, value=1, step=1)

offset = (page_num - 1) * page_size

# Build filters dict
filters = {}
if filter_declarable != "All":
    filters["declarable"] = filter_declarable
if filter_leaf != "All":
    filters["leaf"] = filter_leaf

# Fetch data
result = fetch_commodities(limit=page_size, offset=offset, filters=filters)
total = result["total"]
data = result["data"]

# Client-side description search (the API does exact match, so we filter here)
if search_desc and data:
    search_lower = search_desc.lower()
    data = [r for r in data if search_lower in str(r.get("description", "")).lower()]

if data:
    df = pd.DataFrame(data)

    # Summary metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Total matching records", f"{total:,}")
    m2.metric("Showing", f"{len(data):,}")
    m3.metric("Page", f"{page_num} of {max(1, (total + page_size - 1) // page_size)}")

    st.dataframe(df, use_container_width=True, hide_index=True)

    # Download button
    csv_data = df.to_csv(index=False)
    st.download_button(
        label="⬇️ Download as CSV",
        data=csv_data,
        file_name="commodities_export.csv",
        mime="text/csv",
    )
else:
    st.info("No records found matching your filters.")
