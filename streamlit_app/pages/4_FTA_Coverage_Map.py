"""
Page 4 — FTA Coverage Map
Interactive choropleth world map and Sankey diagram of preferential trade coverage.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from streamlit_app.lib.data import load_geo_areas, load_preferential

st.set_page_config(page_title="FTA Coverage Map", page_icon="🌍", layout="wide")
st.title("🌍 FTA Coverage Map")

prefs = load_preferential()
geo = load_geo_areas()

# Country-level stats
country_prefs = prefs.groupby(["geographical_area_id", "geographical_area_description", "trade_agreement"]).agg(
    commodity_lines=("commodity_code", "count"),
).reset_index()

country_totals = prefs.groupby(["geographical_area_id", "geographical_area_description"]).agg(
    total_lines=("commodity_code", "count"),
    agreements=("trade_agreement", "nunique"),
).reset_index()

# Merge ISO codes from geo areas
country_geo = geo[geo["geographical_area_type"] == "country"][["geographical_area_id", "iso_alpha2_code"]].copy()
country_totals = country_totals.merge(country_geo, on="geographical_area_id", how="left")

# ISO alpha-3 mapping for plotly choropleth (alpha-2 to alpha-3)
iso_map = {
    "AU": "AUS", "BD": "BGD", "CO": "COL", "PE": "PER", "EC": "ECU",
    "KR": "KOR", "ZA": "ZAF", "JP": "JPN", "NO": "NOR", "VN": "VNM",
    "GH": "GHA", "SG": "SGP",
}
country_totals["iso_alpha3"] = country_totals["iso_alpha2_code"].map(iso_map)

# --- Choropleth ---
st.subheader("Preferential Coverage by Country")
st.markdown("Countries shaded by the number of commodity lines with preferential duty rates under UK trade agreements.")

fig = px.choropleth(
    country_totals,
    locations="iso_alpha3",
    color="total_lines",
    hover_name="geographical_area_description",
    hover_data={"total_lines": True, "agreements": True, "iso_alpha3": False},
    color_continuous_scale="Blues",
    labels={"total_lines": "Preferential Lines", "agreements": "Agreements"},
    title="Number of Preferential Commodity Lines by Country",
)
fig.update_layout(
    geo={"showframe": False, "showcoastlines": True, "projection_type": "natural earth"},
    height=500,
    margin={"t": 60, "b": 20, "l": 0, "r": 0},
)
st.plotly_chart(fig, use_container_width=True)

# --- Agreement table ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Trade Agreements")
    agreement_summary = prefs.groupby("trade_agreement").agg(
        countries=("geographical_area_description", lambda x: ", ".join(sorted(x.unique()))),
        commodity_lines=("commodity_code", "count"),
        cumulation=("cumulation_type", "first"),
    ).reset_index()
    st.dataframe(agreement_summary, use_container_width=True, hide_index=True)

with col2:
    st.subheader("Coverage by Country")
    st.dataframe(
        country_totals[["geographical_area_description", "total_lines", "agreements"]].rename(
            columns={"geographical_area_description": "Country", "total_lines": "Preferential Lines", "agreements": "Agreements"}
        ),
        use_container_width=True,
        hide_index=True,
    )

st.divider()

# --- Sankey diagram ---
st.subheader("Trade Agreement → Commodity Chapter Flow")
st.markdown("Sankey diagram showing how preferential lines flow from agreements to commodity chapters.")

prefs_sankey = prefs.copy()
prefs_sankey["chapter"] = prefs_sankey["commodity_code"].str[:2]

flows = prefs_sankey.groupby(["trade_agreement", "chapter"]).size().reset_index(name="count")

# Build node lists
agreements = flows["trade_agreement"].unique().tolist()
chapters = flows["chapter"].unique().tolist()
all_nodes = agreements + [f"Ch. {c}" for c in chapters]

source_idx = [agreements.index(a) for a in flows["trade_agreement"]]
target_idx = [len(agreements) + chapters.index(c) for c in flows["chapter"]]

fig = go.Figure(go.Sankey(
    node={
        "pad": 15,
        "thickness": 20,
        "label": all_nodes,
        "color": ["#1f77b4"] * len(agreements) + ["#ff7f0e"] * len(chapters),
    },
    link={
        "source": source_idx,
        "target": target_idx,
        "value": flows["count"].tolist(),
        "color": "rgba(31, 119, 180, 0.3)",
    },
))
fig.update_layout(title="Preferential Lines: Agreement → Chapter", height=500)
st.plotly_chart(fig, use_container_width=True)

# --- Network graph (cumulation) ---
st.divider()
st.subheader("Cumulation Network")
st.markdown("Countries linked by shared cumulation arrangements under trade agreements.")

cumulation_links = prefs[["geographical_area_description", "trade_agreement", "cumulation_type"]].drop_duplicates()
grouped = cumulation_links.groupby("trade_agreement")["geographical_area_description"].apply(list).reset_index()

edges = []
for _, row in grouped.iterrows():
    countries = row["geographical_area_description"]
    for i in range(len(countries)):
        for j in range(i + 1, len(countries)):
            edges.append({
                "from": countries[i],
                "to": countries[j],
                "agreement": row["trade_agreement"],
            })

if edges:
    edges_df = pd.DataFrame(edges)
    st.dataframe(edges_df.rename(columns={"from": "Country A", "to": "Country B", "agreement": "Agreement"}),
                 use_container_width=True, hide_index=True)
else:
    st.info("No multi-country cumulation links found in the data.")
