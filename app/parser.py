"""CSV-to-JSON parser.

This module contains the parsing logic that converts raw CSV text into
structured JSON. Replace the `parse_csv` function with your own
implementation - the API endpoint calls only this function.
"""

from __future__ import annotations

import csv
import io
import re


def parse_csv(raw_text: str) -> list[dict]:
    """Parse CSV text and return a list of row dictionaries.

    Args:
        raw_text: The full CSV content as a string.

    Returns:
        A list of dicts, one per row, with values coerced to native types.
    """
    reader = csv.DictReader(io.StringIO(raw_text))
    return [{key: _coerce(val) for key, val in row.items() if key is not None} for row in reader]


def _coerce(value: str) -> bool | int | float | str | None:
    """Best-effort coercion of a CSV string value to a native Python type.

    Args:
        value: A single cell value from the CSV.

    Returns:
        The value coerced to its most appropriate Python type.
    """
    if not isinstance(value, str):
        return value
    if not value:
        return None

    upper = value.upper()
    if upper in {"TRUE", "FALSE"}:
        return upper == "TRUE"

    if re.fullmatch(r"-?[1-9]\d*|0", value):
        return int(value)

    try:
        f = float(value)
        if "." in value or "e" in value.lower():
            return f
    except ValueError:
        pass

    return value
