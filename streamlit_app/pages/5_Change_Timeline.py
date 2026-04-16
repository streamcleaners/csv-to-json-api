"""
Page 5 — Commodity Code Change Timeline
Timeline visualisation with anomaly detection.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

from streamlit_app.lib.data import load_changes

st.set_page_config(page_title="Change Timeline", page_icon="📅", layout="wide")
st.title("📅 Commodity Code Change Timeline")

changes = load_changes()

# Filters
change_types = changes["change_type"].unique().tolist()
selected_types = st.multiselect("Filter by change type", change_types, default=change_types)
filtered = changes[changes["change_type"].isin(selected_types)]

# --- Timeline scatter ---
st.subheader("Timeline")

colour_map = {
    "split": "#1f77b4",
    "merge": "#ff7f0e",
    "new": "#2ca02c",
    "end": "#d62728",
    "duty_change": "#9467bd",
    "description_change": "#8c564b",
}

fig = px.scatter(
    filtered,
    x="effective_date",
    y="change_type",
    color="change_type",
    hover_data=["change_id", "old_commodity_code", "new_commodity_code", "reason"],
    title="Commodity Code Changes Over Time",
    labels={"effective_date": "Effective Date", "change_type": "Change Type"},
    color_discrete_map=colour_map,
)
fig.update_traces(marker=dict(size=12))
fig.update_layout(height=350, showlegend=True)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- Stacked bar by quarter ---
st.subheader("Changes by Quarter")

filtered_copy = filtered.copy()
filtered_copy["quarter"] = filtered_copy["effective_date"].dt.to_period("Q").astype(str)

quarter_counts = filtered_copy.groupby(["quarter", "change_type"]).size().reset_index(name="count")

fig = px.bar(
    quarter_counts,
    x="quarter",
    y="count",
    color="change_type",
    title="Volume of Changes by Quarter",
    labels={"quarter": "Quarter", "count": "Number of Changes", "change_type": "Type"},
    color_discrete_map=colour_map,
)
fig.update_layout(barmode="stack", height=400)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- Anomaly detection ---
st.subheader("Anomaly Detection")
st.markdown("Quarters with an unusually high number of changes (>1.5 standard deviations above the mean).")

total_per_quarter = filtered_copy.groupby("quarter").size().reset_index(name="total")
mean_changes = total_per_quarter["total"].mean()
std_changes = total_per_quarter["total"].std()
threshold = mean_changes + 1.5 * std_changes if std_changes > 0 else mean_changes + 1

total_per_quarter["anomaly"] = total_per_quarter["total"] > threshold

anomalies = total_per_quarter[total_per_quarter["anomaly"]]
if not anomalies.empty:
    for _, row in anomalies.iterrows():
        st.warning(f"⚠️ **{row['quarter']}** — {row['total']} changes (threshold: {threshold:.0f})")
else:
    st.success("✅ No anomalous quarters detected.")

# Detail table
st.divider()
st.subheader("Change Detail")
st.dataframe(
    filtered[["change_id", "change_type", "effective_date", "old_commodity_code",
              "new_commodity_code", "old_description", "new_description", "reason"]],
    use_container_width=True,
    hide_index=True,
)
