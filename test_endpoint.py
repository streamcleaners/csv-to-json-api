# ruff: noqa: S310
"""Quick smoke test: send a CSV to the deployed API and print the JSON response.

Usage:
    python test_endpoint.py
"""

from __future__ import annotations

import json
import subprocess
import urllib.request

CSV_CONTENT = b"name,age,active\nAlice,30,TRUE\nBob,25,FALSE\nCharlie,,TRUE\n"

API_URL = (
    subprocess.check_output(
        ["terraform", "output", "-raw", "api_url"],
        cwd="infra",
        text=True,
    ).rstrip("/")
    + "/api/convert"
)

boundary = "----TestBoundary123"
body = (
    (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="test.csv"\r\n'
        f"Content-Type: text/csv\r\n"
        f"\r\n"
    ).encode()
    + CSV_CONTENT
    + f"\r\n--{boundary}--\r\n".encode()
)

req = urllib.request.Request(
    API_URL,
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
)

with urllib.request.urlopen(req) as resp:
    result = json.loads(resp.read())

print(json.dumps(result, indent=2))
