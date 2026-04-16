#!/usr/bin/env bash
# Upload all CSV files from data/ to the S3 data bucket.
# Usage: bash infra/seed_data.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="$ROOT_DIR/data"

BUCKET=$(cd "$SCRIPT_DIR" && terraform output -raw data_bucket)

echo "Uploading CSVs to s3://$BUCKET ..."

for csv_file in "$DATA_DIR"/*.csv; do
  filename=$(basename "$csv_file")
  echo "  $filename"
  aws s3 cp "$csv_file" "s3://$BUCKET/$filename" --quiet
done

echo "Done. Uploaded $(ls "$DATA_DIR"/*.csv | wc -l | tr -d ' ') files."
