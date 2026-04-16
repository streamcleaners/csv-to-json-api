"""
Shared data loading for the Streamlit dashboard.

All data is fetched from the FastAPI CSV-to-JSON API rather than reading
CSV files directly. This decouples the dashboard from the file system and
means we can later swap in CSV uploads, a database, or any other backend
without changing the Streamlit code.

The API base URL defaults to the deployed AWS API Gateway endpoint and can
be overridden with the API_BASE_URL environment variable.
"""

from __future__ import annotations

import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st

API_BASE_URL = os.environ.get("API_BASE_URL", "https://qk011cty71.execute-api.eu-west-2.amazonaws.com")
API_KEY = os.environ.get("API_KEY", "")


def _headers() -> dict[str, str]:
    """Build request headers, including API key if configured."""
    h: dict[str, str] = {}
    if API_KEY:
        h["X-API-Key"] = API_KEY
    return h


def _fetch(resource: str, **params) -> pd.DataFrame:
    """
    Fetch all records for a resource from the API and return as a DataFrame.
    Passes any extra keyword arguments as query-string filters.
    """
    params.setdefault("_limit", "10000")
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{API_BASE_URL}/api/{resource}?{qs}"

    try:
        req = Request(url, headers=_headers())
        with urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
    except URLError as exc:
        st.error(
            f"Could not reach the API at `{API_BASE_URL}`. Make sure it is running (`pixi run serve`).\n\nError: {exc}"
        )
        st.stop()

    rows = body.get("data", [])
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


@st.cache_data(ttl=60)
def load_commodities() -> pd.DataFrame:
    df = _fetch("commodities")
    df["commodity_code"] = df["commodity_code"].astype(str)
    if "parent_commodity_code" in df.columns:
        df["parent_commodity_code"] = df["parent_commodity_code"].astype(str)
    if "commodity_code_indent" in df.columns:
        df["commodity_code_indent"] = pd.to_numeric(df["commodity_code_indent"], errors="coerce").fillna(0).astype(int)
    return df


@st.cache_data(ttl=60)
def load_measures() -> pd.DataFrame:
    df = _fetch("measures_on_declarable_commodities")
    if df.empty:
        return df
    df["commodity_code"] = df["commodity_code"].astype(str)
    df["measure_type_id"] = pd.to_numeric(df["measure_type_id"], errors="coerce")
    df["duty_amount"] = pd.to_numeric(df["duty_amount"], errors="coerce")
    return df


@st.cache_data(ttl=60)
def load_quotas() -> pd.DataFrame:
    df = _fetch("trade_quotas")
    if df.empty:
        return df
    df["commodity_code"] = df["commodity_code"].astype(str)
    for col in ["quota_period_start", "quota_period_end", "last_allocation_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    df["fill_rate_percent"] = pd.to_numeric(df["fill_rate_percent"], errors="coerce")
    df["opening_balance_volume"] = pd.to_numeric(df["opening_balance_volume"], errors="coerce")
    df["critical_threshold_percent"] = pd.to_numeric(df["critical_threshold_percent"], errors="coerce")
    return df


@st.cache_data(ttl=60)
def load_preferential() -> pd.DataFrame:
    df = _fetch("preferential_measures")
    if df.empty:
        return df
    df["commodity_code"] = df["commodity_code"].astype(str)
    return df


@st.cache_data(ttl=60)
def load_changes() -> pd.DataFrame:
    df = _fetch("commodity_code_changes")
    if df.empty:
        return df
    for col in ["old_commodity_code", "new_commodity_code"]:
        if col in df.columns:
            df[col] = df[col].astype(str)
    if "effective_date" in df.columns:
        df["effective_date"] = pd.to_datetime(df["effective_date"], errors="coerce")
    return df


@st.cache_data(ttl=60)
def load_geo_areas() -> pd.DataFrame:
    return _fetch("geographical_areas")


@st.cache_data(ttl=60)
def load_measure_types() -> pd.DataFrame:
    return _fetch("measure_types")


@st.cache_data(ttl=60)
def load_certificates() -> pd.DataFrame:
    df = _fetch("certificates_and_licences")
    if df.empty:
        return df
    df["commodity_code"] = df["commodity_code"].astype(str)
    return df


def upload_csv(filename: str, content: bytes) -> dict:
    """
    Upload a CSV file to the API. Returns the API response dict
    with resource name, endpoint, record count, and columns.
    """
    import io
    import urllib.request

    boundary = "----StreamlitUploadBoundary"
    body = io.BytesIO()
    body.write(f"--{boundary}\r\n".encode())
    body.write(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    body.write(b"Content-Type: text/csv\r\n\r\n")
    body.write(content)
    body.write(f"\r\n--{boundary}--\r\n".encode())

    data = body.getvalue()
    req = urllib.request.Request(
        f"{API_BASE_URL}/api/upload",
        data=data,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            **_headers(),
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except URLError as exc:
        return {"status": "error", "detail": str(exc)}


def list_datasets() -> dict:
    """Fetch the list of all available datasets from the API root."""
    try:
        req = Request(f"{API_BASE_URL}/", headers=_headers())
        with urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
        return body.get("datasets", {})
    except URLError:
        return {}


def fetch_dataset(resource: str) -> pd.DataFrame:
    """Fetch any dataset by resource name. Generic version of the typed loaders."""
    return _fetch(resource)
