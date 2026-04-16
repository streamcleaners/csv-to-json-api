"""CSV-to-JSON API.

Two modes of operation:
1. Stateless: POST /api/convert with a CSV file, get JSON back.
2. Stored: Upload a CSV to POST /api/upload, it gets saved to S3
   and becomes a queryable dataset at GET /api/{resource}.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from starlette.requests import Request

from app.auth import AUTH_ENABLED, VALID_KEYS, require_api_key
from app.parser import parse_csv
from app.s3 import list_datasets, read_csv, write_csv

app = FastAPI(
    title="CSV-to-JSON API",
    description="Upload CSVs to S3, query them as JSON endpoints.",
    version="0.2.0",
)


# ---------------------------------------------------------------------------
# Routes - Discovery
# ---------------------------------------------------------------------------


@app.get("/", tags=["discovery"])
def root() -> dict[str, Any]:
    """List every available dataset with its record count and columns.

    Returns:
        A dict with status and dataset metadata.
    """
    datasets = {}
    for name in list_datasets():
        rows = parse_csv(read_csv(name))
        datasets[name] = {
            "records": len(rows),
            "columns": list(rows[0].keys()) if rows else [],
            "endpoint": f"/api/{name}",
        }
    return {"status": "ok", "auth_enabled": AUTH_ENABLED, "datasets": datasets}


# ---------------------------------------------------------------------------
# Routes - Stateless convert
# ---------------------------------------------------------------------------


@app.post("/api/convert", tags=["convert"])
async def convert(
    file: Annotated[UploadFile, File(...)],
    _key: str | None = Depends(require_api_key),
) -> dict[str, Any]:
    """Parse a CSV file and return JSON without storing it.

    Args:
        file: The uploaded CSV file.

    Returns:
        A dict with filename, record count, columns, and parsed data.

    Raises:
        HTTPException: If the file is not a .csv.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    text = (await file.read()).decode("utf-8-sig")
    rows = parse_csv(text)

    return {
        "filename": file.filename,
        "records": len(rows),
        "columns": list(rows[0].keys()) if rows else [],
        "data": rows,
    }


# ---------------------------------------------------------------------------
# Routes - Upload and store
# ---------------------------------------------------------------------------


@app.post("/api/upload", tags=["upload"])
async def upload(
    file: Annotated[UploadFile, File(...)],
    _key: str | None = Depends(require_api_key),
) -> dict[str, Any]:
    """Upload a CSV file to S3 and register it as a queryable dataset.

    Args:
        file: The uploaded CSV file.

    Returns:
        A dict with the resource name, endpoint, record count, and columns.

    Raises:
        HTTPException: If the file is not a .csv or is empty.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    text = (await file.read()).decode("utf-8-sig")
    rows = parse_csv(text)

    if not rows:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no valid rows")

    resource_name = re.sub(r"[^a-zA-Z0-9_]", "_", file.filename.removesuffix(".csv")).lower().strip("_")
    write_csv(resource_name, text)

    return {
        "status": "ok",
        "resource": resource_name,
        "endpoint": f"/api/{resource_name}",
        "records": len(rows),
        "columns": list(rows[0].keys()),
    }


# ---------------------------------------------------------------------------
# Routes - Dataset querying
# ---------------------------------------------------------------------------


def _filtered_response(
    rows: list[dict],
    limit: int,
    offset: int,
    filters: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Apply filters and pagination to a list of rows.

    Args:
        rows: The full dataset rows.
        limit: Max records to return.
        offset: Number of records to skip.
        filters: Column-value filters to apply.

    Returns:
        A paginated response dict.
    """
    filtered = rows
    if filters:
        for col, val in filters.items():
            filtered = [r for r in filtered if str(r.get(col, "")).lower() == val.lower()]

    total = len(filtered)
    page = filtered[offset : offset + limit]

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
    _key: str | None = Depends(require_api_key),
) -> dict[str, Any]:
    """Return records from a stored dataset with pagination.

    Args:
        resource: The dataset name.
        _limit: Max records to return.
        _offset: Number of records to skip.

    Returns:
        A paginated response dict.

    Raises:
        HTTPException: If the dataset is not found.
    """
    if resource not in list_datasets():
        raise HTTPException(status_code=404, detail=f"Dataset '{resource}' not found")
    rows = parse_csv(read_csv(resource))
    return _filtered_response(rows, _limit, _offset)


# ---------------------------------------------------------------------------
# Middleware - arbitrary query-param filtering
# ---------------------------------------------------------------------------


@app.middleware("http")
async def filter_middleware(request: Request, call_next: Any) -> JSONResponse:
    """Intercept GET /api/{resource} and extract column filters from query params."""
    path = request.url.path
    method = request.method

    if method == "GET" and path.startswith("/api/") and path.count("/") == 2:
        resource = path.split("/")[2]
        available = list_datasets()
        if resource in available:
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
            filters = {k: v for k, v in params.items() if not k.startswith("_")}

            if filters:
                rows = parse_csv(read_csv(resource))
                body = _filtered_response(rows, limit, offset, filters or None)
                return JSONResponse(content=body)

    return await call_next(request)
