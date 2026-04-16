import streamlit as st
import pandas as pd
from pathlib import Path

DATA_DIR = Path("data")

st.set_page_config(page_title="UK Tariff API Explorer", layout="wide")


@st.cache_data
def load_commodities() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "commodities.csv", dtype={"commodity_code": str, "parent_commodity_code": str})
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")
    return df


# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.title("UK Tariff APIs")
api = st.sidebar.radio("Select an API", ["Commodities"], label_visibility="collapsed")

# ── Main content ─────────────────────────────────────────────────────────────
st.title("🇬🇧 UK Tariff API Explorer")

if api == "Commodities":
    st.header("Commodities")
    st.caption("Commodity code hierarchy with descriptions — dummy data for demo purposes.")

    df = load_commodities()

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        search = st.text_input("🔍 Search descriptions", placeholder="e.g. horses")
    with col2:
        code_prefix = st.text_input("Filter by code prefix", placeholder="e.g. 0101")
    with col3:
        declarable_filter = st.selectbox("Declarable", ["All", "Yes", "No"])

    filtered = df.copy()

    if search:
        filtered = filtered[filtered["description"].str.contains(search, case=False, na=False)]
    if code_prefix:
        filtered = filtered[filtered["commodity_code"].str.startswith(code_prefix)]
    if declarable_filter == "Yes":
        filtered = filtered[filtered["declarable"] == True]
    elif declarable_filter == "No":
        filtered = filtered[filtered["declarable"] == False]

    # Summary metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Total codes", len(filtered))
    m2.metric("Declarable", int(filtered["declarable"].sum()))
    m3.metric("Leaf nodes", int(filtered["leaf"].sum()))

    # Data table
    st.dataframe(
        filtered[["commodity_code", "description", "commodity_code_indent", "declarable", "leaf", "start_date"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "commodity_code": st.column_config.TextColumn("Code", width="medium"),
            "description": st.column_config.TextColumn("Description", width="large"),
            "commodity_code_indent": st.column_config.NumberColumn("Indent"),
            "declarable": st.column_config.CheckboxColumn("Declarable"),
            "leaf": st.column_config.CheckboxColumn("Leaf"),
            "start_date": st.column_config.DateColumn("Start Date", format="YYYY-MM-DD"),
        },
    )

    # Detail expander
    with st.expander("📄 JSON preview (first 10 filtered rows)"):
        st.json(filtered.head(10).fillna("").to_dict(orient="records"))
