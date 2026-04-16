"""
Page 1 — Commodity Code Classifier
TF-IDF cosine similarity search to find the best-matching commodity codes
from a free-text product description.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st
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

    # Get top 10 for the chart, top 5 for the detail cards
    top_idx = scores.argsort()[-10:][::-1]

    results = []
    for i in top_idx:
        row = declarable.iloc[i]
        chapter = str(row["commodity_code"])[:2]
        results.append(
            {
                "commodity_code": row["commodity_code"],
                "description": row["description"],
                "similarity": round(float(scores[i]) * 100, 1),  # as percentage
                "chapter": chapter,
                "label": f"{row['commodity_code']} — {row['description'][:40]}",
            }
        )

    results_df = pd.DataFrame(results)

    # --- Summary metrics ---
    best = results_df.iloc[0]
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Best Match", best["commodity_code"])
    col_m2.metric("Similarity", f"{best['similarity']}%")
    col_m3.metric("Chapter", best["chapter"])

    st.divider()

    # --- Horizontal bar chart (top 10) ---
    st.subheader("Top 10 Matches by Similarity")

    fig = px.bar(
        results_df,
        x="similarity",
        y="label",
        orientation="h",
        text=results_df["similarity"].apply(lambda x: f"{x:.1f}%"),
        labels={"similarity": "Similarity (%)", "label": ""},
        color="similarity",
        color_continuous_scale="Blues",
        hover_data={"commodity_code": True, "description": True, "similarity": True, "label": False},
    )
    fig.update_layout(
        yaxis={"autorange": "reversed", "tickfont": {"size": 11}},
        xaxis={"range": [0, max(results_df["similarity"].max() * 1.2, 5)]},
        height=400,
        showlegend=False,
        coloraxis_showscale=False,
        margin={"l": 10},
    )
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- Detail cards for top 5 ---
    st.subheader("Top 5 — Detail")
    top5 = results_df.head(5)

    for idx, r in top5.iterrows():
        with st.expander(f"**{r['commodity_code']}** — {r['description']} ({r['similarity']}%)", expanded=(idx == 0)):
            # Hierarchy tree
            all_comms = load_commodities()
            chain = []
            current = r["commodity_code"]
            while current:
                match_row = all_comms[all_comms["commodity_code"] == current]
                if match_row.empty:
                    break
                crow = match_row.iloc[0]
                chain.append(
                    {
                        "code": current,
                        "description": crow["description"],
                        "indent": int(crow["commodity_code_indent"]),
                    }
                )
                current = crow["parent_commodity_code"] if pd.notna(crow["parent_commodity_code"]) else None

            chain.reverse()
            st.markdown("**Classification hierarchy:**")
            for item in chain:
                indent = "&nbsp;" * 6 * item["indent"]
                if item["code"] == r["commodity_code"]:
                    st.markdown(f"{indent}📌 **`{item['code']}`** {item['description']}", unsafe_allow_html=True)
                else:
                    st.markdown(f"{indent}`{item['code']}` {item['description']}", unsafe_allow_html=True)

    st.divider()

    # --- Similarity distribution across all codes ---
    st.subheader("Similarity Distribution")
    st.markdown("How your query scored against all declarable commodity codes.")

    all_scores = pd.DataFrame(
        {
            "commodity_code": declarable["commodity_code"],
            "similarity": (scores * 100).round(1),
        }
    )
    all_scores = all_scores[all_scores["similarity"] > 0].sort_values("similarity", ascending=False)

    if all_scores.empty:
        st.info("No commodity codes had any similarity to your query. Try different terms.")
    else:
        fig2 = px.histogram(
            all_scores,
            x="similarity",
            nbins=20,
            title="Distribution of Similarity Scores (non-zero only)",
            labels={"similarity": "Similarity (%)", "count": "Commodity Codes"},
            color_discrete_sequence=["#1f77b4"],
        )
        fig2.update_layout(height=300, yaxis_title="Number of Codes")
        st.plotly_chart(fig2, use_container_width=True)

        st.caption(f'{len(all_scores)} of {len(declarable)} codes had non-zero similarity to "{query}".')
