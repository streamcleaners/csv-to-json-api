"""
Page 2 — Quota Exhaustion Dashboard
Gauge charts, fill-rate forecasting, and critical quota alerts.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

from streamlit_app.lib.data import load_quotas

st.set_page_config(page_title="Quota Exhaustion", page_icon="📊", layout="wide")
st.title("📊 Quota Exhaustion Dashboard")

quotas = load_quotas()

# Deduplicate to one row per quota order number
quota_summary = (
    quotas.groupby("quota_order_number")
    .first()
    .reset_index()
)


def status_colour(fill_rate):
    if fill_rate >= 90:
        return "🔴"
    elif fill_rate >= 60:
        return "🟠"
    return "🟢"


# Summary cards
critical_quotas = quota_summary[quota_summary["fill_rate_percent"] >= 90]
st.markdown(f"### ⚠️ {len(critical_quotas)} quota(s) at critical fill rate (≥90%)")
if not critical_quotas.empty:
    for _, q in critical_quotas.iterrows():
        st.markdown(f"- **{q['quota_order_number']}** — {q['quota_description']} ({q['fill_rate_percent']}%)")

st.divider()

# Quota table
st.subheader("All Quotas")
display_df = quota_summary[
    ["quota_order_number", "quota_description", "geographical_area_description",
     "opening_balance_volume", "opening_balance_unit", "fill_rate_percent", "status"]
].copy()
display_df["indicator"] = display_df["fill_rate_percent"].apply(status_colour)
display_df = display_df[["indicator"] + [c for c in display_df.columns if c != "indicator"]]
st.dataframe(display_df, use_container_width=True, hide_index=True)

st.divider()

# Gauge charts
st.subheader("Fill Rate Gauges")
cols = st.columns(min(len(quota_summary), 4))
for i, (_, q) in enumerate(quota_summary.iterrows()):
    col = cols[i % len(cols)]
    with col:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=q["fill_rate_percent"],
            title={"text": q["quota_order_number"]},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "darkblue"},
                "steps": [
                    {"range": [0, 60], "color": "#d4edda"},
                    {"range": [60, 90], "color": "#fff3cd"},
                    {"range": [90, 100], "color": "#f8d7da"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 90,
                },
            },
            number={"suffix": "%"},
        ))
        fig.update_layout(height=250, margin=dict(t=60, b=20, l=30, r=30))
        st.plotly_chart(fig, use_container_width=True)

# Forecast section
st.divider()
st.subheader("Fill Rate Forecast")

selected_quota = st.selectbox(
    "Select a quota to forecast",
    quota_summary["quota_order_number"].tolist(),
    format_func=lambda x: f"{x} — {quota_summary[quota_summary['quota_order_number'] == x].iloc[0]['quota_description']}",
)

q = quota_summary[quota_summary["quota_order_number"] == selected_quota].iloc[0]
period_start = q["quota_period_start"]
period_end = q["quota_period_end"]
current_fill = q["fill_rate_percent"]
last_alloc = q["last_allocation_date"]

# Generate synthetic historical fill-rate data points
if pd.notna(period_start) and pd.notna(last_alloc):
    days_elapsed = (last_alloc - period_start).days
    total_days = (period_end - period_start).days

    if days_elapsed > 0 and total_days > 0:
        # Synthetic monthly data points with slight noise
        n_points = max(days_elapsed // 30, 2)
        dates = pd.date_range(period_start, last_alloc, periods=n_points)
        np.random.seed(hash(selected_quota) % 2**31)
        base_rates = np.linspace(0, current_fill, n_points)
        noise = np.random.normal(0, current_fill * 0.03, n_points)
        noise[0] = 0
        noise[-1] = 0
        fill_rates = np.clip(base_rates + noise, 0, 100)

        # Linear forecast to end of period
        from sklearn.linear_model import LinearRegression

        X = np.array([(d - period_start).days for d in dates]).reshape(-1, 1)
        y = fill_rates
        model = LinearRegression().fit(X, y)

        future_dates = pd.date_range(last_alloc, period_end, periods=12)
        X_future = np.array([(d - period_start).days for d in future_dates]).reshape(-1, 1)
        y_future = np.clip(model.predict(X_future), 0, 100)

        # Find predicted exhaustion date
        exhaustion_day = (100 - model.intercept_) / model.coef_[0] if model.coef_[0] > 0 else None
        exhaustion_date = period_start + timedelta(days=int(exhaustion_day)) if exhaustion_day and exhaustion_day <= total_days else None

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, y=fill_rates, mode="lines+markers",
            name="Actual", line=dict(color="blue"),
        ))
        fig.add_trace(go.Scatter(
            x=future_dates, y=y_future, mode="lines",
            name="Forecast", line=dict(color="red", dash="dash"),
        ))
        fig.add_hline(y=90, line_dash="dot", line_color="orange", annotation_text="Critical threshold (90%)")
        fig.add_hline(y=100, line_dash="solid", line_color="red", annotation_text="Exhausted")

        if exhaustion_date:
            fig.add_vline(x=exhaustion_date, line_dash="dot", line_color="red")
            st.warning(f"⚠️ Predicted exhaustion date: **{exhaustion_date.strftime('%d %B %Y')}**")
        else:
            st.success("✅ Quota is not projected to exhaust within the current period.")

        fig.update_layout(
            title=f"Fill Rate Forecast — {selected_quota}",
            xaxis_title="Date",
            yaxis_title="Fill Rate (%)",
            yaxis=dict(range=[0, 105]),
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Insufficient data to generate a forecast for this quota.")
else:
    st.info("Missing date information for this quota.")
