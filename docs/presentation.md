---
author: Department for Business and Trade
date: MMMM dd, YYYY
paging: "%d / %d"
---

# 🇬🇧 UK Tariff Data Explorer

A data platform and interactive dashboard built on
UK Global Tariff open data.

**Department for Business and Trade**

---

## What is this?

Two things working together:

1. A **FastAPI backend** that turns CSV files into a RESTful JSON API
2. A **Streamlit dashboard** that consumes that API and visualises
   tariff data with ML-powered features

The dashboard never touches the CSV files directly.
All data flows through the API.

---

## Why does that matter?

```
  CSV files ──→ FastAPI ──→ Streamlit dashboard
                  ↑
          (future: uploads,
           database, live feed)
```

- The API is the single source of truth
- Swap CSVs for a database later — no dashboard changes
- Add CSV upload endpoints — dashboard picks them up automatically
- Deploy API and dashboard as separate containers

---

## The Data

Eight datasets modelled on real DBT open data:

- **Commodities** — 86 codes in a parent-child hierarchy
- **Measures** — 62 MFN and preferential duty rates
- **Trade Quotas** — 15 tariff rate quotas with fill rates
- **Preferential Measures** — 24 FTA preferential rates
- **Code Changes** — 15 historical splits, merges, duty changes
- **Geographical Areas** — 42 countries and groups
- **Measure Types** — 24 types of trade measure
- **Certificates** — 24 document requirements

All fictional, but structurally identical to the real thing.

---

## The API

Auto-discovers every CSV in the data directory.
Each file becomes a queryable endpoint.

```
GET /                              → list all datasets
GET /api/commodities               → all commodity codes
GET /api/commodities?declarable=true&_limit=10
GET /api/trade_quotas?status=Open
GET /api/measures_on_declarable_commodities?commodity_code=0201100000
POST /reload                       → hot-reload new data
```

Supports filtering, pagination, and field projection.

---

## The Dashboard — 8 Pages

```
 1. Commodity Code Classifier     ← ML
 2. Quota Exhaustion Dashboard    ← ML
 3. Tariff Landscape Overview     ← ML
 4. FTA Coverage Map
 5. Change Timeline               ← anomaly detection
 6. Document Requirements Checker
 7. Duty Comparison Tool
 8. Tariff Protection Index       ← composite scoring
```

---

## Page 1: Commodity Code Classifier

**Problem:** Traders type "beef" but the tariff says "bovine".

**Solution:** TF-IDF cosine similarity with synonym expansion.

How it works:
- Walk up the commodity hierarchy to build rich descriptions
- Expand formal terms with everyday synonyms
  ("bovine" → "beef cattle cow")
- Vectorise with TF-IDF (word importance scoring)
- Rank all codes by cosine similarity to the query

Search "beef" → gets Boneless (24%), Carcasses (22%), Cattle (16%)

---

## Why not a classifier?

We tried logistic regression first.

- 55 declarable codes, one example each = 55 classes
- Model couldn't learn anything
- Every prediction came back at ~1.9% confidence

Cosine similarity doesn't need training data.
It just measures word overlap. Works perfectly with small datasets.

---

## Page 2: Quota Exhaustion Dashboard

**Problem:** Will this quota still be open when my shipment arrives?

**Solution:** Linear regression on fill-rate time series.

- Gauge charts show current fill (green / amber / red)
- Synthetic monthly data points from period start to now
- Linear model projects forward to period end
- Calculates predicted exhaustion date

Simple, explainable, and honest about uncertainty.

---

## Page 3: Tariff Landscape

**Problem:** What does the UK tariff actually look like?

**Solution:** K-means clustering + PCA.

- Histogram and pie chart of duty rate distribution
- Heatmap of mean duty by commodity chapter
- Build feature vectors per commodity:
  [duty, duty_type, n_preferences, n_certificates]
- Standardise → K-means → PCA to 2D → scatter plot

Reveals natural groupings: zero-rated tech, protected agriculture,
mixed-duty beverages.

---

## Page 4: FTA Coverage Map

**Problem:** Where do we have trade deals and what do they cover?

**Solution:** Data joining + Plotly visualisation.

- Choropleth world map shaded by preferential coverage depth
- Sankey diagram: trade agreements → commodity chapters
- Cumulation network showing shared arrangements

No ML needed — the visual impact speaks for itself.

---

## Page 5: Change Timeline

**Problem:** Is the nomenclature stable or churning?

**Solution:** Z-score anomaly detection.

- Scatter timeline of all changes, colour-coded by type
- Stacked bar chart by quarter
- Flag any quarter with changes > mean + 1.5σ

Simple threshold, appropriate for the data volume.

---

## Pages 6, 7, 8

**Document Checker** — Select a commodity code, see required
certificates with GOV.UK guidance links. Pure lookup.

**Duty Comparison** — Pick a code and countries, see MFN vs
preferential rates side by side. Savings callouts.

**Protection Index** — Weighted composite score ranking chapters
by duty rates, quota pressure, and certificate burden.
Radar chart for comparing chapters.

---

## Algorithm Summary

```
Page  Algorithm               Library
────  ──────────────────────  ────────────
  1   TF-IDF + cosine sim    scikit-learn
  2   Linear regression      scikit-learn
  3   K-means + PCA          scikit-learn
  4   —                      plotly
  5   Z-score threshold      numpy
  6   —                      pandas
  7   —                      pandas
  8   Min-max + weighted     scikit-learn
      composite
```

---

## Tech Stack

```
Layer         Tool            Why
─────         ────            ───
Data          CSV files       Mirrors real DBT open data
API           FastAPI         Auto-discovery, filtering, fast
Dashboard     Streamlit       Rapid prototyping, interactive
ML            scikit-learn    Lightweight, no GPU needed
Viz           Plotly          Interactive charts, maps
Packaging     Pixi            Reproducible environments
Containers    Docker Compose  API + dashboard as services
```

---

## Running It

Locally with Pixi:

```bash
pixi run serve       # start the API on :8000
pixi run dashboard   # start the dashboard on :8501
```

With Docker:

```bash
docker compose up --build
```

API at localhost:8000, dashboard at localhost:8501.

---

## What's Next

- **CSV upload endpoint** — POST a file, it becomes a new dataset
- **Sentence embeddings** — replace TF-IDF for semantic search
- **Real data feed** — pull from data.api.trade.gov.uk
- **Seasonal forecasting** — Prophet for quota predictions
- **Auth** — API keys or OAuth2 on the FastAPI layer
- **Redis caching** — for multi-user deployments

---

# Questions?

```
pixi run serve       → API
pixi run dashboard   → Dashboard
slides docs/presentation.md → This presentation
```

**github.com/streamcleaners/csv-to-json-api**
