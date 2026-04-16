"""
Page 3 — Tariff Landscape Overview
Heatmaps, histograms, pie charts, and clustering of the tariff structure.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from streamlit_app.lib.data import load_measures, load_preferential, load_certificates

st.set_page_config(page_title="Tariff Landscape", page_icon="🗺️", layout="wide")
st.title("🗺️ Tariff Landscape Overview")

measures = load_measures()
prefs = load_preferential()
certs = load_certificates()

# Only MFN (third country) duties
mfn = measures[measures["measure_type_id"] == 103].copy()
mfn["chapter"] = mfn["commodity_code"].astype(str).str[:2]
mfn["commodity_code_description"] = mfn["commodity_code_description"].astype(str)
mfn["chapter_label"] = (
    mfn["chapter"].astype(str) + " — " + mfn["commodity_code_description"].str.split("--").str[0].str.strip()
)

# --- Duty rate distribution ---
st.subheader("Duty Rate Distribution")
col1, col2 = st.columns(2)

with col1:
    fig = px.histogram(
        mfn,
        x="duty_amount",
        nbins=20,
        title="Histogram of MFN Duty Rates",
        labels={"duty_amount": "Duty Rate"},
        color_discrete_sequence=["#1f77b4"],
    )
    fig.update_layout(yaxis_title="Number of Commodity Codes")
    st.plotly_chart(fig, use_container_width=True)

with col2:

    def duty_band(rate):
        if rate == 0:
            return "Zero-rated"
        elif rate <= 5:
            return "Low (0–5%)"
        elif rate <= 12:
            return "Medium (5–12%)"
        return "High (>12%)"

    mfn["duty_band"] = mfn["duty_amount"].apply(duty_band)
    band_counts = mfn["duty_band"].value_counts().reset_index()
    band_counts.columns = ["band", "count"]

    fig = px.pie(
        band_counts,
        values="count",
        names="band",
        title="Commodity Codes by Duty Band",
        color_discrete_sequence=px.colors.sequential.Blues_r,
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- Heatmap: chapter vs duty type ---
st.subheader("Duty Rates by Chapter")

chapter_stats = (
    mfn.groupby("chapter")
    .agg(
        mean_duty=("duty_amount", "mean"),
        max_duty=("duty_amount", "max"),
        count=("commodity_code", "count"),
        pct_zero=("duty_amount", lambda x: (x == 0).mean() * 100),
    )
    .reset_index()
)

fig = go.Figure(
    data=go.Heatmap(
        z=[chapter_stats["mean_duty"].values],
        x=chapter_stats["chapter"].values,
        y=["Mean Duty Rate"],
        colorscale="RdYlGn_r",
        text=[[f"{v:.1f}%" for v in chapter_stats["mean_duty"].values]],
        texttemplate="%{text}",
        hovertemplate="Chapter %{x}<br>Mean duty: %{z:.1f}%<extra></extra>",
    )
)
fig.update_layout(
    title="Mean MFN Duty Rate by Commodity Chapter",
    xaxis_title="Chapter",
    height=200,
    margin=dict(t=60, b=40),
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- Clustering ---
st.subheader("Tariff Profile Clustering")
st.markdown(
    "Commodities clustered by duty amount, duty type, number of preferential agreements, and certificate requirements."
)

# Build feature matrix
pref_counts = prefs.groupby("commodity_code").size().reset_index(name="n_prefs")
cert_counts = certs.groupby("commodity_code").size().reset_index(name="n_certs")

features = mfn[["commodity_code", "duty_amount", "chapter"]].copy()
features["is_specific"] = (mfn["duty_amount_unit"] == "specific").astype(int)
features = features.merge(pref_counts, on="commodity_code", how="left")
features = features.merge(cert_counts, on="commodity_code", how="left")
features["n_prefs"] = features["n_prefs"].fillna(0)
features["n_certs"] = features["n_certs"].fillna(0)

numeric_cols = ["duty_amount", "is_specific", "n_prefs", "n_certs"]
X = features[numeric_cols].values

if len(X) >= 3:
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    n_clusters = st.slider("Number of clusters", 2, 6, 3)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    features["cluster"] = kmeans.fit_predict(X_scaled)

    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(X_scaled)
    features["pc1"] = coords[:, 0]
    features["pc2"] = coords[:, 1]

    fig = px.scatter(
        features,
        x="pc1",
        y="pc2",
        color="cluster",
        hover_data=["commodity_code", "duty_amount", "n_prefs", "n_certs"],
        title="Commodity Clusters (PCA projection)",
        labels={"pc1": "Principal Component 1", "pc2": "Principal Component 2", "cluster": "Cluster"},
        color_continuous_scale="Viridis",
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Cluster summary:**")
    cluster_summary = features.groupby("cluster")[numeric_cols].mean().round(2)
    st.dataframe(cluster_summary, use_container_width=True)
else:
    st.info("Not enough data points for clustering.")
