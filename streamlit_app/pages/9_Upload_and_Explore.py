"""
Page 9 — Upload & Explore
Upload a CSV file, send it to the API, and auto-generate visualisations
based on the detected column types.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from streamlit_app.lib.data import fetch_dataset, list_datasets, upload_csv

st.set_page_config(page_title="Upload & Explore", page_icon="📤", layout="wide")
st.title("📤 Upload & Explore")
st.markdown(
    "Upload any CSV file. It will be parsed by the API, stored as a new dataset, "
    "and this page will auto-generate charts based on the data structure."
)

# ---------------------------------------------------------------------------
# Upload section
# ---------------------------------------------------------------------------
st.subheader("Upload a new CSV")

uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

if uploaded_file is not None:
    with st.spinner("Uploading to API..."):
        result = upload_csv(uploaded_file.name, uploaded_file.getvalue())

    if result.get("status") == "ok":
        st.success(
            f"Uploaded **{uploaded_file.name}** as dataset "
            f"**`{result['resource']}`** — {result['records']} records, "
            f"{len(result['columns'])} columns."
        )
        st.cache_data.clear()
    elif result.get("status") == "error":
        st.error(f"Upload failed: {result.get('detail', 'Unknown error')}")
    else:
        st.error(f"Upload failed: {result}")

st.divider()

# ---------------------------------------------------------------------------
# Dataset explorer
# ---------------------------------------------------------------------------
st.subheader("Explore a dataset")

all_datasets = list_datasets()

if not all_datasets:
    st.warning("No datasets available. Upload a CSV or make sure the API is running.")
    st.stop()

dataset_name = st.selectbox(
    "Select a dataset",
    sorted(all_datasets.keys()),
    format_func=lambda k: f"{k} ({all_datasets[k]['records']} records, {len(all_datasets[k]['columns'])} columns)",
)

df = fetch_dataset(dataset_name)

if df.empty:
    st.info("This dataset is empty.")
    st.stop()

# ---------------------------------------------------------------------------
# Schema detection
# ---------------------------------------------------------------------------


def classify_columns(df: pd.DataFrame) -> dict:
    """Classify each column by its detected type."""
    col_types = {}
    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            col_types[col] = "empty"
            continue

        # Try numeric
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.notna().sum() > len(series) * 0.7:
            col_types[col] = "numeric"
            continue

        # Try datetime
        try:
            dates = pd.to_datetime(series, errors="coerce", format="mixed")
            if dates.notna().sum() > len(series) * 0.7:
                col_types[col] = "datetime"
                continue
        except Exception:
            pass

        # Try boolean
        if series.astype(str).str.upper().isin(["TRUE", "FALSE"]).mean() > 0.8:
            col_types[col] = "boolean"
            continue

        # Categorical vs free text
        nunique = series.nunique()
        if nunique <= 20 or nunique / len(series) < 0.3:
            col_types[col] = "categorical"
        else:
            col_types[col] = "text"

    return col_types


col_types = classify_columns(df)

numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
categorical_cols = [c for c, t in col_types.items() if t == "categorical"]
datetime_cols = [c for c, t in col_types.items() if t == "datetime"]
boolean_cols = [c for c, t in col_types.items() if t == "boolean"]
text_cols = [c for c, t in col_types.items() if t == "text"]

# Convert detected types
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")
for col in datetime_cols:
    df[col] = pd.to_datetime(df[col], errors="coerce", format="mixed")

# ---------------------------------------------------------------------------
# Schema summary
# ---------------------------------------------------------------------------
st.divider()
st.subheader("📋 Detected Schema")

schema_df = pd.DataFrame(
    [
        {"Column": col, "Detected Type": col_types[col], "Non-null": df[col].notna().sum(), "Unique": df[col].nunique()}
        for col in df.columns
    ]
)
st.dataframe(schema_df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Summary metrics
# ---------------------------------------------------------------------------
st.divider()
st.subheader("📊 Summary")

metric_cols = st.columns(4)
metric_cols[0].metric("Rows", f"{len(df):,}")
metric_cols[1].metric("Columns", f"{len(df.columns)}")
metric_cols[2].metric("Numeric", f"{len(numeric_cols)}")
metric_cols[3].metric("Categorical", f"{len(categorical_cols)}")

# ---------------------------------------------------------------------------
# Auto-generated visualisations
# ---------------------------------------------------------------------------
st.divider()
st.subheader("📈 Auto-Generated Visualisations")

# --- Numeric distributions ---
if numeric_cols:
    st.markdown("### Numeric Distributions")
    for i in range(0, len(numeric_cols), 2):
        cols = st.columns(2)
        for j, col_widget in enumerate(cols):
            idx = i + j
            if idx < len(numeric_cols):
                col_name = numeric_cols[idx]
                with col_widget:
                    fig = px.histogram(
                        df,
                        x=col_name,
                        nbins=20,
                        title=f"Distribution of {col_name}",
                        color_discrete_sequence=["#1f77b4"],
                    )
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)

    # Correlation heatmap if 2+ numeric columns
    if len(numeric_cols) >= 2:
        st.markdown("### Correlation Matrix")
        corr = df[numeric_cols].corr()
        fig = px.imshow(
            corr,
            text_auto=".2f",
            color_continuous_scale="RdBu_r",
            title="Numeric Column Correlations",
            zmin=-1,
            zmax=1,
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

# --- Categorical breakdowns ---
if categorical_cols:
    st.markdown("### Categorical Breakdowns")
    for i in range(0, len(categorical_cols), 2):
        cols = st.columns(2)
        for j, col_widget in enumerate(cols):
            idx = i + j
            if idx < len(categorical_cols):
                col_name = categorical_cols[idx]
                counts = df[col_name].value_counts().head(15).reset_index()
                counts.columns = [col_name, "count"]
                with col_widget:
                    fig = px.bar(
                        counts,
                        x=col_name,
                        y="count",
                        title=f"Top values: {col_name}",
                        color_discrete_sequence=["#ff7f0e"],
                    )
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)

# --- Time series ---
if datetime_cols and numeric_cols:
    st.markdown("### Time Series")
    date_col = st.selectbox("Date column", datetime_cols)
    value_col = st.selectbox("Value column", numeric_cols)

    ts_df = df[[date_col, value_col]].dropna().sort_values(date_col)
    if not ts_df.empty:
        fig = px.line(
            ts_df,
            x=date_col,
            y=value_col,
            title=f"{value_col} over {date_col}",
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

# --- Scatter plot for numeric pairs ---
if len(numeric_cols) >= 2:
    st.markdown("### Scatter Plot")
    scatter_cols = st.columns(3)
    with scatter_cols[0]:
        x_col = st.selectbox("X axis", numeric_cols, index=0)
    with scatter_cols[1]:
        y_col = st.selectbox("Y axis", numeric_cols, index=min(1, len(numeric_cols) - 1))
    with scatter_cols[2]:
        color_options = ["None", *categorical_cols]
        color_col = st.selectbox("Colour by", color_options)

    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        color=None if color_col == "None" else color_col,
        title=f"{y_col} vs {x_col}",
        hover_data=df.columns.tolist()[:5],
    )
    fig.update_layout(height=450)
    st.plotly_chart(fig, use_container_width=True)

# --- Boolean summary ---
if boolean_cols:
    st.markdown("### Boolean Summary")
    for col_name in boolean_cols:
        counts = df[col_name].astype(str).str.upper().value_counts().reset_index()
        counts.columns = [col_name, "count"]
        fig = px.pie(counts, values="count", names=col_name, title=f"{col_name}")
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Raw data table
# ---------------------------------------------------------------------------
st.divider()
st.subheader("🗂️ Raw Data")

st.dataframe(df, use_container_width=True, hide_index=True)

csv_export = df.to_csv(index=False)
st.download_button(
    label="⬇️ Download as CSV",
    data=csv_export,
    file_name=f"{dataset_name}_export.csv",
    mime="text/csv",
)
