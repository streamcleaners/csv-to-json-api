#!/usr/bin/env bash
# Deploy application code to the existing Lambda function.
# Run this after any changes to app/ code (e.g. parser.py).
# For infrastructure changes, use: cd infra && terraform apply
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Build the lambda package
echo "Building lambda package..."
bash "$SCRIPT_DIR/build_lambda.sh"

# Zip it
echo "Creating zip..."
cd "$ROOT_DIR/lambda_package"
zip -r "$ROOT_DIR/lambda_package.zip" . -q
cd "$ROOT_DIR"

# Get function name from Terraform output
FUNCTION_NAME=$(cd "$SCRIPT_DIR" && terraform output -raw lambda_function_name)

# Deploy to Lambda
echo "Deploying to $FUNCTION_NAME..."
aws lambda update-function-code \
  --function-name "$FUNCTION_NAME" \
  --zip-file "fileb://$ROOT_DIR/lambda_package.zip" \
  --no-cli-pager

echo "Deployed successfully."
