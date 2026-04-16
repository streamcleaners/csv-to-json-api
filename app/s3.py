"""S3 helpers for reading and writing CSV datasets."""

from __future__ import annotations

import os

import boto3

BUCKET = os.environ.get("DATA_BUCKET", "")

_client = boto3.client("s3")


def list_datasets() -> list[str]:
    """Return the stem names of all .csv objects in the bucket.

    Returns:
        A list of dataset names (e.g. ["commodities", "trade_quotas"]).
    """
    if not BUCKET:
        return []
    resp = _client.list_objects_v2(Bucket=BUCKET)
    return [obj["Key"].removesuffix(".csv") for obj in resp.get("Contents", []) if obj["Key"].endswith(".csv")]


def read_csv(name: str) -> str:
    """Read a CSV file from S3 and return its text content.

    Args:
        name: Dataset name (without .csv extension).

    Returns:
        The raw CSV text.
    """
    resp = _client.get_object(Bucket=BUCKET, Key=f"{name}.csv")
    return resp["Body"].read().decode("utf-8-sig")


def write_csv(name: str, content: str) -> None:
    """Write CSV text to S3.

    Args:
        name: Dataset name (without .csv extension).
        content: The raw CSV text.
    """
    _client.put_object(Bucket=BUCKET, Key=f"{name}.csv", Body=content.encode("utf-8"))
