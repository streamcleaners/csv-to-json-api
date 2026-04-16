---
author: Department for Business and Trade
date: MMMM dd, YYYY
paging: "%d / %d"
---

# UK Tariff Data Explorer

A data platform and interactive dashboard built on
UK Global Tariff open data.

**Department for Business and Trade**

---

## What is this?

Two things working together:

1. A **FastAPI backend** that parses, stores, and serves CSV data
   as a RESTful JSON API — backed by S3
2. A **Streamlit dashboard** that consumes that API and visualises
   data with ML-powered features

The dashboard never touches files directly.
All data flows through the API.

---

## Architecture

```
  S3 bucket
      |
  FastAPI (Lambda + API Gateway)
      |
      |--- GET  /api/{resource}     query datasets
      |--- POST /api/upload         upload new CSVs
      |--- POST /api/convert        stateless parse
      |--- X-API-Key auth           protects all endpoints
      |
  Streamlit dashboard
      |
      |--- 9 pages of visualisation and ML
      |--- Upload & Explore for any CSV
```

---

## What we built (the full list)

- ~~Dummy tariff CSV data~~ Done
- ~~FastAPI CSV-to-JSON API~~ Done
- ~~Streamlit dashboard (8 ML/viz pages)~~ Done
- ~~CSV upload endpoint + auto-viz page~~ Done
- ~~API key authentication~~ Done
- ~~GitHub Actions CI/CD~~ Done
- ~~Docker Compose~~ Done
- ~~AWS deployment (Lambda + S3)~~ Done
- ~~Terminal presentation~~ Done

---

## The Data

Eight tariff datasets plus user-uploaded CSVs:

- **Commodities** — 86 codes in a parent-child hierarchy
- **Measures** — 62 MFN and preferential duty rates
- **Trade Quotas** — 15 tariff rate quotas with fill rates
- **Preferential Measures** — 24 FTA preferential rates
- **Code Changes** — 15 historical splits, merges, duty changes
- **Geographical Areas** — 42 countries and groups
- **Measure Types** — 24 types of trade measure
- **Certificates** — 24 document requirements

Plus sample uploads: water quality, environmental surveys.

---

## The API

```
GET  /                     list datasets + auth status
GET  /api/{resource}       query with filters + pagination
POST /api/upload           upload CSV, store in S3
POST /api/convert          stateless CSV to JSON
```

All /api/* endpoints protected by X-API-Key header.
Auth disabled by default for local dev, enabled via
API_KEYS environment variable.

---

## Authentication

```
# Disabled (default) — local dev just works
pixi run serve

# Enabled — set API_KEYS on the API, API_KEY on dashboard
API_KEYS=my-secret pixi run serve
API_KEY=my-secret  pixi run dashboard
```

- Keys from env var (comma-separated) or file
- No key = 401, wrong key = 403, valid key = 200
- Root / endpoint stays open (health check)
- Dashboard passes key automatically via X-API-Key header

---

## The Dashboard — 9 Pages

```
 1. Commodity Code Classifier     <- ML (TF-IDF)
 2. Quota Exhaustion Dashboard    <- ML (linear regression)
 3. Tariff Landscape Overview     <- ML (K-means + PCA)
 4. FTA Coverage Map              <- choropleth + Sankey
 5. Change Timeline               <- anomaly detection
 6. Document Requirements Checker
 7. Duty Comparison Tool
 8. Tariff Protection Index       <- composite scoring
 9. Upload and Explore            <- auto-generated viz
```

---

## Page 1: Commodity Code Classifier

**Problem:** Traders type "beef" but the tariff says "bovine".

**Solution:** TF-IDF cosine similarity with synonym expansion.

- Walk up the commodity hierarchy for rich descriptions
- Expand formal terms with everyday synonyms
- Vectorise with TF-IDF, rank by cosine similarity

Search "beef" -> Boneless (24%), Carcasses (22%), Cattle (16%)

We tried logistic regression first — 55 classes, one example
each, every prediction at 1.9%. Cosine similarity just works.

---

## Page 2: Quota Exhaustion Dashboard

**Problem:** Will this quota still be open when my shipment arrives?

**Solution:** Linear regression on fill-rate time series.

- Gauge charts: green / amber / red
- Linear model projects forward to period end
- Calculates predicted exhaustion date

Simple, explainable, honest about uncertainty.

---

## Pages 3-5: Landscape, Map, Timeline

**Tariff Landscape** — K-means clustering + PCA.
Histogram, pie chart, heatmap, scatter plot of clusters.

**FTA Coverage Map** — Plotly choropleth world map,
Sankey diagram, cumulation network.

**Change Timeline** — Z-score anomaly detection.
Scatter timeline, stacked bar by quarter, anomaly alerts.

---

## Pages 6-8: Checker, Comparison, Index

**Document Checker** — Select a commodity code, see required
certificates with GOV.UK guidance links.

**Duty Comparison** — Pick a code and countries, see MFN vs
preferential rates side by side with savings callouts.

**Protection Index** — Weighted composite score ranking chapters.
Radar chart for comparing chapters.

---

## Page 9: Upload and Explore

Upload any CSV. The system:

1. Sends it to POST /api/upload (stored in S3)
2. Auto-detects column types (numeric, categorical, date, boolean)
3. Generates visualisations based on what it finds:
   - Numeric -> histograms + correlation heatmap
   - Categorical -> bar charts of top values
   - Date + numeric -> time series line chart
   - 2+ numeric -> interactive scatter plot
   - Boolean -> pie charts

Works for tariff data, water quality, environmental surveys,
or anything else in CSV format.

---

## Algorithm Summary

```
Page  Algorithm               Library
----  ----------------------  ------------
  1   TF-IDF + cosine sim    scikit-learn
  2   Linear regression      scikit-learn
  3   K-means + PCA          scikit-learn
  4   -                      plotly
  5   Z-score threshold      numpy
  6   -                      pandas
  7   -                      pandas
  8   Min-max + weighted     scikit-learn
  9   Auto type detection    pandas
```

---

## Tech Stack

```
Layer         Tool              Why
-----         ----              ---
Storage       S3                Serverless, scalable
API           FastAPI + Lambda  Auto-discovery, fast, serverless
Auth          API key (X-API-Key) Simple, stateless, rotatable
Dashboard     Streamlit         Rapid prototyping, interactive
ML            scikit-learn      Lightweight, no GPU needed
Viz           Plotly            Interactive charts, maps
Packaging     Pixi              Reproducible environments
Containers    Docker Compose    Local dev with both services
CI/CD         GitHub Actions    Lint, test, security, Docker
IaC           Terraform         AWS infrastructure as code
```

---

## Running It

Locally:
```bash
pixi run serve       # API on :8002
pixi run dashboard   # dashboard on :8501
```

Docker:
```bash
docker compose up --build
```

With auth:
```bash
API_KEYS=secret pixi run serve
API_KEY=secret pixi run dashboard
```

---

## What's Next

- **Sentence embeddings** — replace TF-IDF for semantic search
- **Real data feed** — pull from data.api.trade.gov.uk
- **Seasonal forecasting** — Prophet for quota predictions
- **Redis caching** — for multi-user deployments
- **Role-based access** — read-only vs upload permissions
- **Audit logging** — track who uploaded what and when

---

# Questions?

```
pixi run serve       -> API
pixi run dashboard   -> Dashboard
slides docs/presentation.md -> This presentation
```

**github.com/streamcleaners/csv-to-json-api**
