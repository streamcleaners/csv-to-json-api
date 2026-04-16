#!/usr/bin/env bash
# Build the Lambda deployment package into lambda_package/
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PKG_DIR="$ROOT_DIR/lambda_package"

rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR"

# Install Python dependencies (Lambda-compatible)
pip install fastapi mangum python-multipart --target "$PKG_DIR" --quiet --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.12

# Copy application code
cp -r "$ROOT_DIR/app" "$PKG_DIR/app"

echo "Lambda package built at $PKG_DIR"
