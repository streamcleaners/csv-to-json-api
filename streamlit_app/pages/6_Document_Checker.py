"""
Page 6 — Document Requirements Checker
Look up required certificates and licences by commodity code.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px

from streamlit_app.lib.data import load_certificates, load_commodities

st.set_page_config(page_title="Document Checker", page_icon="📋", layout="wide")
st.title("📋 Document Requirements Checker")

certs = load_certificates()
comms = load_commodities()

# --- Lookup ---
st.subheader("Look Up by Commodity Code")

declarable = comms[comms["declarable"] == True]  # noqa: E712
code_options = declarable["commodity_code"].tolist()
descriptions = dict(zip(declarable["commodity_code"], declarable["description"]))

selected_code = st.selectbox(
    "Select a commodity code",
    code_options,
    format_func=lambda c: f"{c} — {descriptions.get(c, '')}",
)

matching = certs[certs["commodity_code"] == selected_code]

if matching.empty:
    st.success(f"✅ No document requirements found for **{selected_code}**.")
else:
    st.info(f"📄 This commodity requires **{len(matching)} document(s)** for import/export.")

    for _, row in matching.iterrows():
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"### {row['document_code']} — {row['document_description']}")
                st.markdown(f"**Measure:** {row['measure_type_description']}")
                st.markdown(f"**Applies to:** {row['geographical_area_description']}")
                st.markdown(f"**From:** {row['start_date']}")
            with col2:
                if pd.notna(row.get("guidance_url")) and row["guidance_url"]:
                    st.link_button("📖 GOV.UK Guidance", row["guidance_url"])
            st.divider()

# --- Overview chart ---
st.divider()
st.subheader("Most Common Document Requirements")

doc_counts = certs.groupby(["document_code", "document_description"]).size().reset_index(name="count")
doc_counts["label"] = doc_counts["document_code"] + " — " + doc_counts["document_description"]

fig = px.bar(
    doc_counts.sort_values("count", ascending=True),
    x="count",
    y="label",
    orientation="h",
    title="Document Requirements Across All Commodities",
    labels={"count": "Number of Commodity Codes", "label": "Document"},
    color="count",
    color_continuous_scale="Blues",
)
fig.update_layout(height=400, showlegend=False)
st.plotly_chart(fig, use_container_width=True)

# --- Measure type breakdown ---
st.subheader("Requirements by Measure Type")
measure_counts = certs.groupby("measure_type_description").size().reset_index(name="count")
fig = px.pie(
    measure_counts,
    values="count",
    names="measure_type_description",
    title="Document Requirements by Control Type",
    color_discrete_sequence=px.colors.qualitative.Set2,
)
st.plotly_chart(fig, use_container_width=True)
