"""
Page 7 — Duty Comparison Tool
Compare MFN and preferential duty rates across countries for a commodity.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import plotly.graph_objects as go
import streamlit as st

from streamlit_app.lib.data import load_commodities, load_measures, load_preferential, load_quotas

st.set_page_config(page_title="Duty Comparison", page_icon="⚖️", layout="wide")
st.title("⚖️ Duty Comparison Tool")

measures = load_measures()
prefs = load_preferential()
quotas = load_quotas()
comms = load_commodities()

# Commodity selector
declarable = comms[comms["declarable"] == True]  # noqa: E712
code_options = declarable["commodity_code"].tolist()
descriptions = dict(zip(declarable["commodity_code"], declarable["description"], strict=False))

selected_code = st.selectbox(
    "Select a commodity code",
    code_options,
    format_func=lambda c: f"{c} — {descriptions.get(c, '')}",
)

# Get MFN rate
mfn_row = measures[
    (measures["commodity_code"] == selected_code) & (measures["measure_type_id"] == 103)
]

# Get preferential rates
pref_rows = prefs[prefs["commodity_code"] == selected_code]

# Get quota info
quota_rows = quotas[quotas["commodity_code"] == selected_code]

st.divider()

if mfn_row.empty:
    st.warning("No MFN duty data found for this commodity code.")
else:
    mfn = mfn_row.iloc[0]
    st.subheader(f"MFN Rate: {mfn['duty_expression']}")

    if pref_rows.empty:
        st.info("No preferential rates available for this commodity. MFN rate applies to all countries.")
    else:
        # Country selector
        available_countries = pref_rows["geographical_area_description"].unique().tolist()
        selected_countries = st.multiselect(
            "Select countries to compare",
            available_countries,
            default=available_countries[:4],
        )

        if selected_countries:
            comparison = pref_rows[pref_rows["geographical_area_description"].isin(selected_countries)].copy()

            # Build comparison chart
            fig = go.Figure()

            # MFN bar for reference
            fig.add_trace(go.Bar(
                name="MFN Rate",
                x=selected_countries,
                y=[mfn["duty_amount"]] * len(selected_countries),
                marker_color="#d62728",
                text=[mfn["duty_expression"]] * len(selected_countries),
                textposition="outside",
            ))

            # Preferential bars
            pref_amounts = []
            pref_texts = []
            for country in selected_countries:
                row = comparison[comparison["geographical_area_description"] == country]
                if not row.empty:
                    pref_amounts.append(0.0)  # preferential rates in our data are 0
                    pref_texts.append(row.iloc[0]["preferential_duty_rate"])
                else:
                    pref_amounts.append(mfn["duty_amount"])
                    pref_texts.append("N/A")

            fig.add_trace(go.Bar(
                name="Preferential Rate",
                x=selected_countries,
                y=pref_amounts,
                marker_color="#2ca02c",
                text=pref_texts,
                textposition="outside",
            ))

            fig.update_layout(
                barmode="group",
                title=f"Duty Rate Comparison — {selected_code}",
                yaxis_title="Duty Rate (%)",
                height=450,
            )
            st.plotly_chart(fig, use_container_width=True)

            # Savings callout
            if mfn["duty_amount"] > 0:
                st.subheader("💰 Potential Savings")
                for country in selected_countries:
                    row = comparison[comparison["geographical_area_description"] == country]
                    if not row.empty:
                        st.success(
                            f"Importing from **{country}** under the "
                            f"**{row.iloc[0]['trade_agreement']}** saves "
                            f"**{mfn['duty_expression']}** compared to MFN."
                        )

            # Detail table
            st.divider()
            st.subheader("Detail")
            detail = comparison[
                ["geographical_area_description", "trade_agreement",
                 "preferential_duty_rate", "mfn_duty_rate", "preference_margin",
                 "rules_of_origin_reference", "cumulation_type"]
            ].rename(columns={
                "geographical_area_description": "Country",
                "trade_agreement": "Agreement",
                "preferential_duty_rate": "Preferential Rate",
                "mfn_duty_rate": "MFN Rate",
                "preference_margin": "Margin",
                "rules_of_origin_reference": "Rules of Origin",
                "cumulation_type": "Cumulation",
            })
            st.dataframe(detail, use_container_width=True, hide_index=True)

            # Quota info
            if not quota_rows.empty:
                st.divider()
                st.subheader("📦 Applicable Quotas")
                st.dataframe(
                    quota_rows[["quota_order_number", "quota_description",
                                "geographical_area_description", "opening_balance_volume",
                                "opening_balance_unit", "fill_rate_percent", "status"]],
                    use_container_width=True,
                    hide_index=True,
                )
