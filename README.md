# csv-to-json-api

A data pipeline that ingests publicly available CSV datasets (such as UK tariff data from data.gov.uk), transforms them into JSON, and exposes them through a RESTful API. Includes a multi-page Streamlit dashboard for interactive data exploration, ML-powered classification, and CSV upload.

## Prerequisites

- [Pixi](https://pixi.sh) package manager, or
- [Docker](https://www.docker.com/products/docker-desktop/)

Install Pixi:

```bash
curl -fsSL https://pixi.sh/install.sh | bash
```

## Setup

```bash
pixi install
```

## Running the application

### Option 1: Pixi (local)

Run each in a separate terminal:

```bash
# API server — http://localhost:8000
pixi run serve

# Streamlit dashboard — http://localhost:8501
pixi run dashboard
```

### Option 2: Docker Compose

```bash
docker compose up --build
```

Or detached: `docker compose up --build -d`

- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:8501

## Available pixi tasks

| Task | Command | Description |
|---|---|---|
| `pixi run serve` | `uvicorn app.main:app --reload --port 8000` | Start the API server |
| `pixi run dashboard` | `streamlit run streamlit_app/Home.py` | Start the Streamlit dashboard |
| `pixi run test` | `pytest tests/ -v --tb=short` | Run the test suite |
| `pixi run lint` | `ruff check .` | Lint the codebase |
| `pixi run format` | `ruff format --check .` | Check code formatting |
| `pixi run deploy` | `bash infra/deploy.sh` | Deploy to AWS Lambda |

## API endpoints

All CSV files in `data/` are auto-discovered and served as JSON endpoints.

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | List all available datasets with record counts and columns |
| `/api/{resource}` | GET | Query a dataset with pagination and filtering |
| `/api/{resource}/{index}` | GET | Get a single record by 0-based index |
| `/api/upload` | POST | Upload a CSV file to create a new dataset |
| `/api/convert` | POST | Parse a CSV and return JSON without storing |
| `/reload` | POST | Reload all datasets from disk |

### Included datasets

| Dataset | Endpoint |
|---|---|
| Commodities | `/api/commodities` |
| Certificates and Licences | `/api/certificates_and_licences` |
| Commodity Code Changes | `/api/commodity_code_changes` |
| Geographical Areas | `/api/geographical_areas` |
| Measure Types | `/api/measure_types` |
| Measures on Declarable Commodities | `/api/measures_on_declarable_commodities` |
| Preferential Measures | `/api/preferential_measures` |
| Trade Quotas | `/api/trade_quotas` |

### Query parameters

- `_limit` — max records to return (default 100, max 10000)
- `_offset` — number of records to skip
- `_fields` — comma-separated list of columns to include
- Any other parameter is treated as a column filter, e.g. `?declarable=true`

### Upload a CSV

```bash
curl -X POST http://localhost:8000/api/upload -F "file=@my_data.csv"
```

The file is saved to `data/` and immediately queryable as a new endpoint.

## Dashboard pages

| Page | Description |
|---|---|
| Home | Overview and navigation |
| Commodity Code Classifier | ML-powered product description to commodity code prediction |
| Quota Exhaustion | Monitor quota fill rates and forecast exhaustion dates |
| Tariff Landscape | Heatmaps, histograms, and clustering of the tariff structure |
| FTA Coverage Map | Interactive world map of preferential trade coverage |
| Change Timeline | Timeline of commodity code changes with anomaly detection |
| Document Checker | Look up required certificates and licences by commodity |
| Duty Comparison | Compare duty rates across countries for a commodity |
| Protection Index | Composite protection score ranking by commodity chapter |
| Upload & Explore | Upload any CSV and get auto-generated visualisations |

## CI/CD

GitHub Actions workflows run on push and PR to `main`:

- **CI** — linting (ruff), type checking (mypy), tests (pytest), Docker build and smoke test
- **Security** — secret scanning (TruffleHog), dependency review, CodeQL analysis, pip-audit

## Deployment

Infrastructure is managed with Terraform in `infra/`. The API deploys as an AWS Lambda function behind API Gateway:

```bash
pixi run deploy
```

## Project structure

```
├── app/
│   ├── main.py               # FastAPI application
│   ├── parser.py              # CSV parsing and type coercion
│   ├── csv_loader.py          # CSV file loading
│   ├── handler.py             # AWS Lambda handler (Mangum)
│   └── streamlit_app.py       # Standalone Streamlit frontend
├── streamlit_app/
│   ├── Home.py                # Dashboard home page
│   ├── pages/                 # 9 dashboard sub-pages
│   └── lib/                   # Dashboard utilities
├── data/                      # CSV data files (auto-discovered)
├── tests/                     # Test suite (pytest)
├── infra/                     # Terraform infrastructure (Lambda, API Gateway)
├── docs/                      # Documentation and presentations
├── sample_uploads/            # Example CSV files for upload testing
├── .github/workflows/         # CI and security pipelines
├── Dockerfile                 # Container image
├── docker-compose.yml         # Multi-service orchestration
├── pixi.toml                  # Pixi dependencies and tasks
├── ruff.toml                  # Linter configuration
└── requirements.txt           # Pip dependencies (Docker)
```

---

*Data is entirely fictional and for demonstration purposes only.*
