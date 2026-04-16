"""Quick smoke test: send a CSV to the deployed API and print the JSON response.

Usage:
    pixi run python test_endpoint.py
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

API_URL = "https://qk011cty71.execute-api.eu-west-2.amazonaws.com/api/convert"
CSV_FILE = Path("data/commodities.csv")

response = httpx.post(API_URL, files={"file": (CSV_FILE.name, CSV_FILE.read_bytes(), "text/csv")})
response.raise_for_status()

print(json.dumps(response.json(), indent=2))
