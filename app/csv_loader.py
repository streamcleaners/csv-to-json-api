"""
Generic CSV loader that auto-discovers CSV files in a directory and converts
each one into a list of dictionaries.  Values are coerced to native Python
types (int, float, bool, None) where possible so the JSON output is typed
rather than all-strings.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path


def _coerce(value):
    """Best-effort coercion of a CSV string value to a native Python type."""
    if not isinstance(value, str):
        return value
    if value == "":
        return None

    # Booleans
    if value.upper() == "TRUE":
        return True
    if value.upper() == "FALSE":
        return False

    # Integers (no leading zeros except "0" itself)
    if re.fullmatch(r"-?[1-9]\d*|0", value):
        return int(value)

    # Floats
    try:
        f = float(value)
        if "." in value or "e" in value.lower():
            return f
    except ValueError:
        pass

    return value


def load_csv(path: Path) -> list[dict]:
    """Read a single CSV file and return a list of row dicts."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        return [
            {key: _coerce(val) for key, val in row.items() if key is not None}
            for row in reader
        ]
