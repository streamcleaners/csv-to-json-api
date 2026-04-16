"""
Page 8 — Tariff Protection Index
Composite protection score ranking by commodity chapter.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.preprocessing import MinMaxScaler

from streamlit_app.lib.data import load_measures, load_quotas, load_certificates, load_preferential

st.set_page_config(page_title="Protection Index", page_icon="🛡️", layout="wide")
st.title("🛡️ Tariff Protection Index")
st.markdown(
    "Composite score ranking commodity chapters by how 'protected' they are, "
    "combining duty rates, quota restrictions, and certificate requirements."
)

measures = load_measures()
quotas = load_quotas()
certs = load_certificates()
prefs = load_preferential()

# MFN only
mfn = measures[measures["measure_type_id"] == 103].copy()
mfn["chapter"] = mfn["commodity_code"].astype(str).str[:2]

# --- Build chapter-level features ---
chapter_duty = mfn.groupby("chapter").agg(
    mean_duty=("duty_amount", "mean"),
    max_duty=("duty_amount", "max"),
    n_commodities=("commodity_code", "nunique"),
).reset_index()

# Quota pressure: count of quota lines per chapter
quotas_ch = quotas.copy()
quotas_ch["chapter"] = quotas_ch["commodity_code"].astype(str).str[:2]
quota_pressure = quotas_ch.groupby("chapter").agg(
    n_quota_lines=("commodity_code", "count"),
    mean_fill_rate=("fill_rate_percent", "mean"),
).reset_index()

# Certificate burden
certs_ch = certs.copy()
certs_ch["chapter"] = certs_ch["commodity_code"].astype(str).str[:2]
cert_burden = certs_ch.groupby("chapter").agg(
    n_cert_requirements=("commodity_code", "count"),
).reset_index()

# Merge
index_df = chapter_duty.merge(quota_pressure, on="chapter", how="left")
index_df = index_df.merge(cert_burden, on="chapter", how="left")
index_df = index_df.fillna(0)

# Normalise each component to 0–1
components = ["mean_duty", "max_duty", "mean_fill_rate", "n_cert_requirements"]
scaler = MinMaxScaler()
if len(index_df) > 1:
    index_df[components] = scaler.fit_transform(index_df[components])
else:
    index_df[components] = 0.5

# Weighted composite
weights = {"mean_duty": 0.35, "max_duty": 0.20, "mean_fill_rate": 0.25, "n_cert_requirements": 0.20}
index_df["protection_score"] = sum(index_df[col] * w for col, w in weights.items())
index_df = index_df.sort_values("protection_score", ascending=False)

# Chapter labels
chapter_labels = {
    "01": "Live animals",
    "02": "Meat",
    "03": "Fish",
    "08": "Fruit & nuts",
    "22": "Beverages",
    "61": "Knitted apparel",
    "84": "Machinery",
    "85": "Electrical equipment",
    "94": "Furniture",
}
index_df["chapter_label"] = index_df["chapter"].map(lambda c: f"Ch. {c} — {chapter_labels.get(c, 'Other')}")

# --- Horizontal bar chart ---
st.subheader("Protection Score by Chapter")

fig = px.bar(
    index_df,
    x="protection_score",
    y="chapter_label",
    orientation="h",
    color="protection_score",
    color_continuous_scale="Reds",
    text=index_df["protection_score"].apply(lambda x: f"{x:.2f}"),
    labels={"protection_score": "Protection Score", "chapter_label": "Chapter"},
    title="Chapters Ranked by Composite Protection Score",
)
fig.update_layout(yaxis=dict(autorange="reversed"), height=450, showlegend=False)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- Radar chart ---
st.subheader("Chapter Detail — Radar Chart")

col1, col2 = st.columns([1, 2])

with col1:
    selected_chapters = st.multiselect(
        "Select chapters to compare (max 3)",
        index_df["chapter_label"].tolist(),
        default=index_df["chapter_label"].tolist()[:2],
        max_selections=3,
    )

with col2:
    if selected_chapters:
        radar_components = ["mean_duty", "max_duty", "mean_fill_rate", "n_cert_requirements"]
        radar_labels = ["Mean Duty Rate", "Max Duty Rate", "Quota Fill Pressure", "Certificate Burden"]

        fig = go.Figure()
        colours = ["#1f77b4", "#ff7f0e", "#2ca02c"]

        for i, chapter_label in enumerate(selected_chapters):
            row = index_df[index_df["chapter_label"] == chapter_label].iloc[0]
            values = [row[c] for c in radar_components]
            values.append(values[0])  # close the polygon

            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=radar_labels + [radar_labels[0]],
                fill="toself",
                name=chapter_label,
                line_color=colours[i % len(colours)],
                opacity=0.6,
            ))

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            title="Protection Profile Comparison",
            height=450,
        )
        st.plotly_chart(fig, use_container_width=True)

# --- Weights explanation ---
st.divider()
st.subheader("Methodology")
st.markdown(
    """
    The protection score is a weighted composite of four normalised (0–1) components:

    | Component | Weight | Source |
    |-----------|--------|--------|
    | Mean duty rate | 35% | MFN measures |
    | Max duty rate | 20% | MFN measures |
    | Quota fill pressure | 25% | Trade quotas (mean fill rate) |
    | Certificate burden | 20% | Certificates & licences (count) |

    Each component is min-max scaled across chapters. The composite score
    ranges from 0 (least protected) to 1 (most protected).
    """
)

# Raw data
st.divider()
st.subheader("Raw Data")
display = index_df[["chapter_label", "protection_score", "mean_duty", "max_duty",
                     "mean_fill_rate", "n_cert_requirements", "n_commodities"]].rename(columns={
    "chapter_label": "Chapter",
    "protection_score": "Score",
    "mean_duty": "Mean Duty (norm)",
    "max_duty": "Max Duty (norm)",
    "mean_fill_rate": "Quota Pressure (norm)",
    "n_cert_requirements": "Cert Burden (norm)",
    "n_commodities": "Commodities",
})
st.dataframe(display, use_container_width=True, hide_index=True)
