"""
UK Tariff Data Explorer — Home page.
"""

import streamlit as st

st.set_page_config(
    page_title="UK Tariff Data Explorer",
    page_icon="🇬🇧",
    layout="wide",
)

st.title("🇬🇧 UK Tariff Data Explorer")
st.markdown(
    """
    Interactive dashboard built on dummy UK Global Tariff open data from the
    Department for Business and Trade.

    Use the sidebar to navigate between views.

    ---

    ### Pages

    | Page | Description |
    |------|-------------|
    | **Commodity Code Classifier** | Type a product description and get predicted commodity codes |
    | **Quota Exhaustion Dashboard** | Monitor quota fill rates and forecast exhaustion dates |
    | **Tariff Landscape** | Heatmaps, histograms, and clustering of the tariff structure |
    | **FTA Coverage Map** | Interactive world map of preferential trade coverage |
    | **Change Timeline** | Timeline of commodity code changes with anomaly detection |
    | **Document Checker** | Look up required certificates and licences by commodity |
    | **Duty Comparison** | Compare duty rates across countries for a commodity |
    | **Protection Index** | Composite protection score ranking by commodity chapter |

    ---
    *Data is entirely fictional and for demonstration purposes only.*

    **Note:** This dashboard fetches data from the FastAPI backend.
    Make sure the API is running (`pixi run serve`) before using the dashboard.
    """
)
