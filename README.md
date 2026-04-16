# csv-to-json-api

This project builds a scalable data pipeline on AWS infrastructure that ingests publicly available CSV datasets (such as UK tariff data from data.gov.uk), transforms them into JSON format, and exposes them through a RESTful API deployed on AWS infrastructure. The pipeline leverages AWS services for data processing, storage, and API hosting, ensuring reliability and scalability. Additionally, we will apply machine learning models to analyze the transformed data, enabling predictive analytics, pattern detection, or data-driven insights that add value beyond raw data access.

## Prerequisites

- [Pixi](https://pixi.sh) package manager

Install Pixi if you don't have it:

```bash
curl -fsSL https://pixi.sh/install.sh | bash
```

## Setup

Install all dependencies:

```bash
pixi install
```

## Running the application

The app has two components — a FastAPI backend and a Streamlit frontend. Run each in a separate terminal.

### API server

```bash
pixi run serve
```

The API will be available at `http://localhost:8002`. Interactive docs are at `http://localhost:8002/docs`.

### Streamlit dashboard

```bash
pixi run dashboard
```

The dashboard will open at `http://localhost:8501`.

## Running tests

```bash
pixi run test
```

## API endpoints

All CSV files in the `data/` directory are auto-discovered and served as JSON endpoints:

| Endpoint | Description |
|---|---|
| `GET /` | List all available datasets |
| `GET /api/commodities` | Commodity codes and descriptions |
| `GET /api/certificates_and_licences` | Required certificates and licences |
| `GET /api/commodity_code_changes` | Historical commodity code changes |
| `GET /api/geographical_areas` | Geographical area definitions |
| `GET /api/measure_types` | Measure type definitions |
| `GET /api/measures_on_declarable_commodities` | Measures applied to declarable commodities |
| `GET /api/preferential_measures` | Preferential trade measures |
| `GET /api/trade_quotas` | Trade quota allocations |
| `POST /reload` | Reload all datasets from disk |

### Query parameters

- `_limit` — max records to return (default 100, max 10000)
- `_offset` — number of records to skip
- `_fields` — comma-separated list of columns to include
- Any other parameter is treated as a column filter, e.g. `?declarable=true`

### Single record

```
GET /api/{resource}/{index}
```

Returns a single record by its 0-based positional index.

## Project structure

```
├── app/
│   ├── main.py              # FastAPI application
│   ├── csv_loader.py         # CSV loading and type coercion
│   └── streamlit_app.py      # Streamlit frontend
├── data/                     # CSV data files (auto-discovered)
├── tests/                    # Test suite
├── pixi.toml                 # Pixi project config and dependencies
└── requirements.txt          # Pip fallback dependencies
```
