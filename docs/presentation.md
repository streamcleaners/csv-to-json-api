---
author: Department for Business and Trade
date: April 2026
paging: "%d / %d"
---

# UK Tariff Data Explorer

Upload any CSV. Get an API. See it visualised.

**Department for Business and Trade - Hackathon 2026**

---

## The Problem

Government teams sit on mountains of CSV data.

- Tariff schedules, quota allocations, trade agreements
- Locked in spreadsheets, hard to share, harder to visualise
- Every new dataset needs a new pipeline

What if you could just **upload a CSV** and get an API + dashboard automatically?

---

## What We Built

```
                    +------------------+
  Upload CSV  --->  |  AWS Lambda API  |  ---> S3 Storage
                    +------------------+
                            |
                    +------------------+
                    |    Streamlit     |  ---> Interactive Dashboard
                    |   (AWS EC2)     |
                    +------------------+
```

Three pieces, fully deployed on AWS:

1. **API** - Lambda + API Gateway (serverless, scales to zero)
2. **Storage** - S3 bucket (all data lives here)
3. **Dashboard** - Streamlit on EC2 (visualisation layer)

---

## How It Works

Upload a CSV file:

```
POST /api/upload  (with CSV file)
  --> parses CSV, stores in S3
  --> returns: resource name, endpoint, record count
```

Query it immediately:

```
GET /api/commodities              --> all records as JSON
GET /api/commodities?_limit=10    --> paginated
GET /api/trade_quotas?status=Open --> filtered
GET /                             --> list all datasets
```

Stateless convert (no storage):

```
POST /api/convert  --> CSV in, JSON out, nothing stored
```

---

## The Data

Nine datasets seeded from fictional UK trade data:

| Dataset | Records | What it covers |
|---------|---------|----------------|
| Commodities | 86 | Tariff code hierarchy |
| Measures | 62 | MFN and preferential duty rates |
| Trade Quotas | 15 | Quota fill rates and volumes |
| Preferential Measures | 24 | FTA rates |
| Code Changes | 15 | Historical nomenclature changes |
| Geographical Areas | 42 | Countries and trade groups |
| Certificates | 24 | Document requirements |
| Water Quality | 80 | Environmental sample data |

All stored in S3, served through the API.

---

## The Dashboard - 8 Pages

```
 1. Commodity Code Classifier     <-- TF-IDF search
 2. Quota Exhaustion Dashboard    <-- Linear regression
 3. Tariff Landscape Overview     <-- K-means clustering
 4. FTA Coverage Map              <-- Choropleth + Sankey
 5. Change Timeline               <-- Anomaly detection
 6. Document Requirements Checker
 7. Duty Comparison Tool
 8. Tariff Protection Index       <-- Composite scoring
```

Every page reads from the live AWS API endpoint.

---

## ML Highlights

**Commodity Classifier** - Type "beef", find "bovine".
TF-IDF cosine similarity with synonym expansion.
No training data needed.

**Quota Forecasting** - Linear regression on fill-rate
time series. Predicts exhaustion dates.

**Tariff Clustering** - K-means on duty rates, preferences,
certificates. PCA projection to 2D scatter.

**Anomaly Detection** - Z-score flagging on quarterly
nomenclature changes.

---

## Infrastructure

```
Resource              Service         Cost
--------              -------         ----
API                   Lambda          Free tier
API routing           API Gateway     Free tier
Data storage          S3              Free tier
Dashboard hosting     EC2 t3.micro    Free tier
```

All managed by Terraform. One command to deploy, one to destroy.

```bash
cd infra && terraform apply     # deploy everything
cd infra && terraform destroy   # tear it all down
```

---

## Deploy Workflow

Infrastructure (run once):
```bash
cd infra && terraform apply
pixi run seed-data              # upload CSVs to S3
```

Code updates:
```bash
pixi run deploy                 # update Lambda API
pixi run deploy-streamlit       # update dashboard
```

No downtime. No containers to rebuild for API changes.

---

## The Vision: AI-Powered Dashboards

The upload endpoint is the foundation for something bigger.

```
  Upload CSV
      |
      v
  AWS Bedrock (AI)
      |
      +--> "This looks like geographical data"
      |     --> auto-generate choropleth map
      |
      +--> "This has time series columns"
      |     --> auto-generate trend charts
      |
      +--> "This has categorical + numeric data"
            --> auto-generate comparison plots
```

Upload any CSV. AI analyses the schema and data patterns.
New Streamlit dashboard tabs generated automatically.

---

## What That Looks Like

1. User uploads `water_quality.csv`
2. Bedrock sees: lat/lon columns, numeric measurements, dates
3. Auto-generates:
   - Map of sampling sites
   - Time series of pH levels
   - Compliance heatmap by region
4. New dashboard tab appears instantly

No code changes. No manual configuration.
The data describes itself.

---

## Tech Stack

```
Layer         Tool              Why
-----         ----              ---
API           FastAPI + Mangum  Serverless, auto-docs
Compute       AWS Lambda        Scales to zero, free tier
Storage       AWS S3            Durable, cheap, simple
Gateway       API Gateway v2    HTTP API, low latency
Dashboard     Streamlit         Rapid prototyping
Hosting       EC2 t3.micro      Free tier, Docker
ML            scikit-learn      Lightweight, no GPU
Viz           Plotly            Interactive charts, maps
IaC           Terraform         Reproducible infra
Packaging     Pixi              Reproducible environments
AI (future)   AWS Bedrock       Schema analysis, code gen
```

---

## Live Demo

API endpoint:
```
https://qk011cty71.execute-api.eu-west-2.amazonaws.com/
```

Dashboard:
```
http://<streamlit-ip>:8501
```

---

# Questions?

**github.com/streamcleaners/csv-to-json-api**
