"""CSV-to-JSON API.

Two modes of operation:
1. Stateless: POST /api/convert with a CSV file, get JSON back.
2. Stored: Upload a CSV to /api/upload, it gets saved to the data directory
   and becomes a queryable dataset at GET /api/{resource}.

The parsing logic lives in app.parser.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.auth import AUTH_ENABLED, VALID_KEYS, require_api_key
from app.parser import parse_csv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))

# ---------------------------------------------------------------------------
# Dataset storage
# ---------------------------------------------------------------------------
datasets: dict[str, list[dict]] = {}


def _discover_datasets() -> None:
    """Scan DATA_DIR for .csv files and load them into memory."""
    datasets.clear()
    if not DATA_DIR.is_dir():
        return
    for csv_path in sorted(DATA_DIR.glob("*.csv")):
        with open(csv_path, encoding="utf-8-sig") as fh:
            text = fh.read()
        datasets[csv_path.stem] = parse_csv(text)


_discover_datasets()

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="CSV-to-JSON API",
    description=(
        "Generic RESTful API that serves CSV files as JSON. "
        "Upload new CSVs and they become queryable endpoints automatically."
    ),
    version="0.2.0",
)


# ---------------------------------------------------------------------------
# Routes — Discovery
# ---------------------------------------------------------------------------


@app.get("/", tags=["discovery"])
def root():
    """List every available dataset with its record count and columns."""
    return {
        "status": "ok",
        "auth_enabled": AUTH_ENABLED,
        "datasets": {
            name: {
                "records": len(rows),
                "columns": list(rows[0].keys()) if rows else [],
                "endpoint": f"/api/{name}",
            }
            for name, rows in datasets.items()
        },
    }


# ---------------------------------------------------------------------------
# Routes — Stateless convert
# ---------------------------------------------------------------------------


@app.post("/api/convert", tags=["convert"])
async def convert(
    file: Annotated[UploadFile, File(...)],
    _key: str | None = Depends(require_api_key),
) -> dict[str, Any]:
    """Parse a CSV file and return JSON without storing it."""
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    content = await file.read()
    text = content.decode("utf-8-sig")
    rows = parse_csv(text)

    return {
        "filename": file.filename,
        "records": len(rows),
        "columns": list(rows[0].keys()) if rows else [],
        "data": rows,
    }


# ---------------------------------------------------------------------------
# Routes — Upload and store
# ---------------------------------------------------------------------------


@app.post("/api/upload", tags=["upload"])
async def upload(
    file: Annotated[UploadFile, File(...)],
    _key: str | None = Depends(require_api_key),
) -> dict[str, Any]:
    """Upload a CSV file, save it to the data directory, and register it as a dataset."""
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    content = await file.read()
    text = content.decode("utf-8-sig")
    rows = parse_csv(text)

    if not rows:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no valid rows")

    # Sanitise filename to a safe resource name
    stem = Path(file.filename).stem
    resource_name = re.sub(r"[^a-zA-Z0-9_]", "_", stem).lower().strip("_")

    # Save to data directory
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest = DATA_DIR / f"{resource_name}.csv"
    dest.write_text(text, encoding="utf-8")

    # Register in memory
    datasets[resource_name] = rows

    return {
        "status": "ok",
        "resource": resource_name,
        "endpoint": f"/api/{resource_name}",
        "records": len(rows),
        "columns": list(rows[0].keys()),
    }


@app.post("/reload", tags=["admin"])
def reload_datasets(_key: str | None = Depends(require_api_key)):
    """Re-scan the data directory and reload all CSVs."""
    _discover_datasets()
    return {"status": "ok", "datasets_loaded": list(datasets.keys())}


# ---------------------------------------------------------------------------
# Routes — Dataset querying
# ---------------------------------------------------------------------------


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
            filtered = [r for r in filtered if str(r.get(col, "")).lower() == val.lower()]

    total = len(filtered)
    page = filtered[offset : offset + limit]

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


@app.get("/api/{resource}", tags=["data"])
def get_collection(
    resource: str,
    _limit: int = Query(default=100, ge=1, le=10000, alias="_limit"),
    _offset: int = Query(default=0, ge=0, alias="_offset"),
    _fields: str | None = Query(default=None, alias="_fields"),
    _key: str | None = Depends(require_api_key),
):
    """Return records from a stored dataset with filtering and pagination."""
    if resource not in datasets:
        raise HTTPException(status_code=404, detail=f"Dataset '{resource}' not found")
    return _filtered_response(datasets[resource], _limit, _offset, _fields)


@app.get("/api/{resource}/{index}", tags=["data"])
def get_record(resource: str, index: int, _key: str | None = Depends(require_api_key)):
    """Return a single record by its positional index (0-based)."""
    if resource not in datasets:
        raise HTTPException(status_code=404, detail=f"Dataset '{resource}' not found")
    rows = datasets[resource]
    if index < 0 or index >= len(rows):
        raise HTTPException(status_code=404, detail=f"Index {index} out of range (0-{len(rows) - 1})")
    return rows[index]


# ---------------------------------------------------------------------------
# Middleware — arbitrary query-param filtering
# ---------------------------------------------------------------------------


@app.middleware("http")
async def filter_middleware(request: Request, call_next):
    """Intercept GET /api/{resource} and extract column filters from query params."""
    path = request.url.path
    method = request.method

    if method == "GET" and path.startswith("/api/") and path.count("/") == 2:
        resource = path.split("/")[2]
        if resource in datasets:
            # Check auth if enabled
            if AUTH_ENABLED:
                key = request.headers.get("X-API-Key")
                if not key:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Missing API key. Provide it in the X-API-Key header."},
                    )
                if key not in VALID_KEYS:
                    return JSONResponse(status_code=403, content={"detail": "Invalid API key."})

            params = dict(request.query_params)
            limit = int(params.pop("_limit", "100"))
            offset = int(params.pop("_offset", "0"))
            fields = params.pop("_fields", None)
            filters = {k: v for k, v in params.items() if not k.startswith("_")}

            body = _filtered_response(datasets[resource], limit, offset, fields, filters or None)
            return JSONResponse(content=body)

    return await call_next(request)
