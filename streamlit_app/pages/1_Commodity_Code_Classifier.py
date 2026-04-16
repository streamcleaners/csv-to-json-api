"""
Page 1 — Commodity Code Classifier
TF-IDF cosine similarity search to find the best-matching commodity codes
from a free-text product description.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from streamlit_app.lib.data import load_commodities

st.set_page_config(page_title="Commodity Classifier", page_icon="🔍", layout="wide")
st.title("🔍 Commodity Code Classifier")
st.markdown("Type a plain-English product description and get the best-matching commodity codes.")


@st.cache_resource
def build_search_index():
    df = load_commodities()
    declarable = df[df["declarable"] == True].copy()  # noqa: E712
    declarable = declarable.dropna(subset=["description"])
    declarable["description"] = declarable["description"].astype(str)

    # Common trade synonyms to enrich matching.
    # Maps everyday terms to the formal language used in tariff descriptions.
    synonyms = {
        "bovine": "beef cattle cow",
        "equine": "horse pony",
        "swine": "pig pork",
        "ovine": "sheep lamb",
        "poultry": "chicken turkey duck",
        "carcasses": "beef meat whole",
        "boneless": "beef meat fillet steak",
        "bananas": "banana fruit tropical",
        "plantains": "plantain banana cooking",
        "data-processing": "computer laptop pc desktop",
        "portable automatic data-processing": "laptop notebook computer",
        "cellular networks": "mobile phone smartphone cellphone",
        "storage units": "hard drive ssd disk storage",
        "apparel": "clothing clothes garment",
        "knitted": "knit knitwear jumper sweater",
        "overcoats": "coat jacket outerwear",
        "cotton": "cotton fabric textile",
        "man-made fibres": "polyester nylon synthetic",
        "spirits": "alcohol liquor spirit drink",
        "whiskies": "whisky whiskey scotch bourbon",
        "cognac": "brandy cognac spirit",
        "wine": "wine grape vino",
        "sparkling wine": "champagne prosecco sparkling fizz",
        "seats": "chair seat seating",
        "upholstered": "sofa couch armchair upholstered",
        "furniture": "furniture furnishing",
        "ornamental fish": "aquarium fish pet tropical",
        "trout": "trout salmon fish",
        "eels": "eel fish",
        "carp": "carp fish freshwater",
    }

    # Build a "full description" by walking up the hierarchy, then append synonyms.
    all_comms = df.set_index("commodity_code")
    full_descs = []
    for _, row in declarable.iterrows():
        parts = [row["description"]]
        parent = row["parent_commodity_code"]
        while pd.notna(parent) and parent in all_comms.index:
            parent_row = all_comms.loc[parent]
            parts.append(str(parent_row["description"]))
            parent = parent_row["parent_commodity_code"] if pd.notna(parent_row["parent_commodity_code"]) else None
        full = " ".join(reversed(parts)).lower()

        # Append synonym expansions for any matching terms
        extras = []
        for term, expansion in synonyms.items():
            if term.lower() in full:
                extras.append(expansion)
        if extras:
            full = full + " " + " ".join(extras)

        full_descs.append(full)

    declarable["full_description"] = full_descs

    vectoriser = TfidfVectorizer(ngram_range=(1, 2), max_features=1000)
    tfidf_matrix = vectoriser.fit_transform(declarable["full_description"])

    return vectoriser, tfidf_matrix, declarable.reset_index(drop=True)


vectoriser, tfidf_matrix, declarable = build_search_index()

query = st.text_input(
    "Describe your product",
    placeholder='e.g. "frozen boneless beef", "cotton men\'s jacket", "laptop computer"',
)

if query:
    query_vec = vectoriser.transform([query])
    scores = cosine_similarity(query_vec, tfidf_matrix).flatten()
    top_idx = scores.argsort()[-5:][::-1]

    results = []
    for i in top_idx:
        row = declarable.iloc[i]
        results.append({
            "commodity_code": row["commodity_code"],
            "description": row["description"],
            "similarity": float(scores[i]),
        })

    results_df = pd.DataFrame(results)

    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader("Top 5 Matches")
        for _, r in results_df.iterrows():
            pct = f"{r['similarity']:.1%}"
            st.markdown(f"**`{r['commodity_code']}`** — {r['description']}  \n*Similarity: {pct}*")

    with col2:
        fig = px.bar(
            results_df,
            x="similarity",
            y="commodity_code",
            orientation="h",
            text=results_df["similarity"].apply(lambda x: f"{x:.1%}"),
            labels={"similarity": "Similarity", "commodity_code": "Commodity Code"},
            title="Match Similarity",
            color="similarity",
            color_continuous_scale="Blues",
        )
        fig.update_layout(yaxis=dict(autorange="reversed"), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # Hierarchy tree for top match
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
        chain.append({
            "code": current,
            "description": row["description"],
            "indent": int(row["commodity_code_indent"]),
        })
        current = row["parent_commodity_code"] if pd.notna(row["parent_commodity_code"]) else None

    chain.reverse()
    for item in chain:
        prefix = "→ " * item["indent"]
        st.markdown(f"{prefix}**`{item['code']}`** {item['description']}")
