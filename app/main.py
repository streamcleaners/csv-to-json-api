"""Stateless CSV-to-JSON API.

Send a CSV file, get JSON back. No storage, no state.
The parsing logic lives in app.parser - swap it out as needed.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.parser import parse_csv

app = FastAPI(
    title="CSV-to-JSON API",
    description="Upload a CSV file and receive parsed JSON. Stateless - nothing is stored.",
    version="0.1.0",
)


@app.get("/")
def health() -> dict[str, str]:
    """Health check / info endpoint.

    Returns:
        A dict with status and usage info.
    """
    return {
        "status": "ok",
        "usage": "POST /api/convert with a CSV file to get JSON back",
    }


@app.post("/api/convert")
async def convert(file: Annotated[UploadFile, File(...)]) -> dict[str, Any]:
    """Accept a CSV file and return the parsed JSON.

    The parsing is handled by `app.parser.parse_csv` - replace that
    function to change how CSV data is transformed.

    Args:
        file: The uploaded CSV file.

    Returns:
        A dict containing filename, record count, column names, and parsed data.

    Raises:
        HTTPException: If the uploaded file is not a .csv.
    """
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
