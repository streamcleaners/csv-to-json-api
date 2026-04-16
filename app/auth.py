"""
API key authentication for the CSV-to-JSON API.

Keys are loaded from the API_KEYS environment variable (comma-separated)
or from a file at API_KEYS_FILE (one key per line).

If neither is set, authentication is disabled and all requests are allowed.
This makes local development frictionless while production deployments
can enforce auth by setting the env var.

Usage:
    # Single key
    API_KEYS=my-secret-key-123

    # Multiple keys
    API_KEYS=key-for-dashboard,key-for-external-client,key-for-ci

    # From a file
    API_KEYS_FILE=/run/secrets/api_keys

Clients authenticate by sending the key in the X-API-Key header:
    curl -H "X-API-Key: my-secret-key-123" http://localhost:8000/api/commodities
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

# ---------------------------------------------------------------------------
# Load keys
# ---------------------------------------------------------------------------

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _load_keys() -> set[str]:
    """Load API keys from environment or file. Returns empty set if none configured."""
    keys: set[str] = set()

    # From env var (comma-separated)
    env_keys = os.environ.get("API_KEYS", "")
    if env_keys:
        keys.update(k.strip() for k in env_keys.split(",") if k.strip())

    # From file (one per line)
    keys_file = os.environ.get("API_KEYS_FILE", "")
    if keys_file:
        path = Path(keys_file)
        if path.is_file():
            keys.update(
                line.strip() for line in path.read_text().splitlines() if line.strip() and not line.startswith("#")
            )

    return keys


VALID_KEYS = _load_keys()
AUTH_ENABLED = len(VALID_KEYS) > 0


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------


async def require_api_key(api_key: str | None = Security(_api_key_header)) -> str | None:
    """
    FastAPI dependency that validates the X-API-Key header.

    If no keys are configured (AUTH_ENABLED is False), all requests pass through.
    If keys are configured, a valid key must be provided.
    """
    if not AUTH_ENABLED:
        return None

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide it in the X-API-Key header.",
        )

    if api_key not in VALID_KEYS:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key.",
        )

    return api_key
