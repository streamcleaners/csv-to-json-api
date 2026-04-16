"""
FastAPI application that auto-discovers every CSV file in a configurable data
directory and exposes each one as a RESTful JSON endpoint.

The CSV file name becomes the resource name:
    data/commodities.csv          ->  GET /api/commodities
    data/trade_quotas.csv         ->  GET /api/trade_quotas
    data/my_water_readings.csv    ->  GET /api/my_water_readings

Each endpoint supports:
    - Full collection:   GET /api/{resource}
    - Single record:     GET /api/{resource}/{index}
    - Query filtering:   GET /api/{resource}?column=value&...
    - Pagination:        GET /api/{resource}?_limit=20&_offset=0

A root endpoint lists all available datasets and their record counts.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from app.csv_loader import load_csv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))

# ---------------------------------------------------------------------------
# Bootstrap: discover and load every CSV at startup
# ---------------------------------------------------------------------------
datasets: dict[str, list[dict]] = {}


def _discover_datasets() -> None:
    """Scan DATA_DIR for .csv files and load them into memory."""
    datasets.clear()
    if not DATA_DIR.is_dir():
        return
    for csv_path in sorted(DATA_DIR.glob("*.csv")):
        resource_name = csv_path.stem          # e.g. "commodities"
        datasets[resource_name] = load_csv(csv_path)


_discover_datasets()

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="CSV-to-JSON API",
    description=(
        "Generic RESTful API that serves any CSV file as JSON. "
        "Drop CSV files into the data directory and they become "
        "queryable endpoints automatically."
    ),
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", tags=["discovery"])
def root():
    """List every available dataset with its record count and columns."""
    return {
        "datasets": {
            name: {
                "records": len(rows),
                "columns": list(rows[0].keys()) if rows else [],
                "endpoint": f"/api/{name}",
            }
            for name, rows in datasets.items()
        }
    }


@app.post("/reload", tags=["admin"])
def reload_datasets():
    """Re-scan the data directory and reload all CSVs."""
    _discover_datasets()
    return {"status": "ok", "datasets_loaded": list(datasets.keys())}


@app.get("/api/{resource}", tags=["data"])
def get_collection(
    resource: str,
    _limit: int = Query(default=100, ge=1, le=10000, alias="_limit"),
    _offset: int = Query(default=0, ge=0, alias="_offset"),
    _fields: str | None = Query(default=None, alias="_fields"),
):
    """
    Return records from a dataset.

    Any query parameter that is *not* a control parameter (prefixed with _)
    is treated as a column filter:  ?commodity_code=0201100000

    Control parameters:
        _limit   – max records to return (default 100)
        _offset  – number of records to skip
        _fields  – comma-separated list of columns to include
    """
    if resource not in datasets:
        raise HTTPException(status_code=404, detail=f"Dataset '{resource}' not found")

    rows = datasets[resource]

    # --- filtering (any non-underscore query param) ---
    # FastAPI doesn't give us raw query params easily, so we grab them from
    # the request scope via a small workaround: we accept **kwargs isn't
    # possible, so we'll parse from the request directly in a dependency-free
    # way by re-reading the query string.
    return _filtered_response(rows, _limit, _offset, _fields)


@app.api_route("/api/{resource}", methods=["GET"], include_in_schema=False)
async def get_collection_filtered(resource: str, _limit: int = 100, _offset: int = 0, _fields: str | None = None):
    """Overloaded to handle arbitrary query-param filtering."""
    # This is intentionally unreachable — the real filtering happens in the
    # middleware below.
    pass  # pragma: no cover


def _filtered_response(
    rows: list[dict],
    limit: int,
    offset: int,
    fields: str | None,
    filters: dict[str, str] | None = None,
) -> dict[str, Any]:
    filtered = rows

    if filters:
        for col, val in filters.items():
            filtered = [
                r for r in filtered
                if str(r.get(col, "")).lower() == val.lower()
            ]

    total = len(filtered)
    page = filtered[offset : offset + limit]

    # field projection
    if fields:
        keep = [f.strip() for f in fields.split(",")]
        page = [{k: v for k, v in row.items() if k in keep} for row in page]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "count": len(page),
        "data": page,
    }


@app.get("/api/{resource}/{index}", tags=["data"])
def get_record(resource: str, index: int):
    """Return a single record by its positional index (0-based)."""
    if resource not in datasets:
        raise HTTPException(status_code=404, detail=f"Dataset '{resource}' not found")

    rows = datasets[resource]
    if index < 0 or index >= len(rows):
        raise HTTPException(status_code=404, detail=f"Index {index} out of range (0–{len(rows) - 1})")

    return rows[index]


# ---------------------------------------------------------------------------
# Middleware to capture arbitrary query-param filters
# ---------------------------------------------------------------------------
from starlette.requests import Request
from starlette.routing import Match


@app.middleware("http")
async def filter_middleware(request: Request, call_next):
    """
    Intercept GET /api/{resource} requests and extract arbitrary query
    parameters as column filters before handing off to the route handler.
    """
    path = request.url.path
    method = request.method

    if method == "GET" and path.startswith("/api/") and path.count("/") == 2:
        resource = path.split("/")[2]
        if resource in datasets:
            params = dict(request.query_params)
            limit = int(params.pop("_limit", "100"))
            offset = int(params.pop("_offset", "0"))
            fields = params.pop("_fields", None)

            # Everything left is a column filter
            filters = {k: v for k, v in params.items() if not k.startswith("_")}

            body = _filtered_response(
                datasets[resource], limit, offset, fields, filters or None
            )
            return JSONResponse(content=body)

    return await call_next(request)
