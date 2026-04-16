"""
Page 1 — Commodity Code Classifier
TF-IDF + Logistic Regression to predict commodity codes from free text.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from streamlit_app.lib.data import load_commodities

st.set_page_config(page_title="Commodity Classifier", page_icon="🔍", layout="wide")
st.title("🔍 Commodity Code Classifier")
st.markdown("Type a plain-English product description and get predicted commodity codes.")


@st.cache_resource
def build_classifier():
    df = load_commodities()
    declarable = df[df["declarable"] == True].copy()  # noqa: E712
    declarable = declarable.dropna(subset=["description"])
    declarable["description"] = declarable["description"].astype(str)
    declarable["chapter"] = declarable["commodity_code"].astype(str).str[:2]

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=500)),
        ("clf", LogisticRegression(max_iter=1000)),
    ])
    pipeline.fit(declarable["description"], declarable["commodity_code"])
    return pipeline, declarable


pipeline, declarable = build_classifier()

query = st.text_input(
    "Describe your product",
    placeholder='e.g. "frozen boneless beef", "cotton men\'s jacket", "laptop computer"',
)

if query:
    probas = pipeline.predict_proba([query])[0]
    classes = pipeline.classes_
    top_idx = probas.argsort()[-5:][::-1]

    results = []
    for i in top_idx:
        code = classes[i]
        row = declarable[declarable["commodity_code"] == code].iloc[0]
        results.append({
            "commodity_code": code,
            "description": row["description"],
            "confidence": probas[i],
        })

    results_df = pd.DataFrame(results)

    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader("Top 5 Predictions")
        for _, r in results_df.iterrows():
            pct = f"{r['confidence']:.1%}"
            st.markdown(f"**`{r['commodity_code']}`** — {r['description']}  \n*Confidence: {pct}*")

    with col2:
        fig = px.bar(
            results_df,
            x="confidence",
            y="commodity_code",
            orientation="h",
            text=results_df["confidence"].apply(lambda x: f"{x:.1%}"),
            labels={"confidence": "Confidence", "commodity_code": "Commodity Code"},
            title="Prediction Confidence",
            color="confidence",
            color_continuous_scale="Blues",
        )
        fig.update_layout(yaxis=dict(autorange="reversed"), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # Hierarchy tree
    st.subheader("Commodity Hierarchy")
    top_code = results_df.iloc[0]["commodity_code"]
    all_comms = load_commodities()
    chain = []
    current = top_code
    while current:
        match = all_comms[all_comms["commodity_code"] == current]
        if match.empty:
            break
        row = match.iloc[0]
        chain.append({"code": current, "description": row["description"], "indent": int(row["commodity_code_indent"])})
        current = row["parent_commodity_code"] if pd.notna(row["parent_commodity_code"]) else None

    chain.reverse()
    for item in chain:
        prefix = "→ " * item["indent"]
        st.markdown(f"{prefix}**`{item['code']}`** {item['description']}")
