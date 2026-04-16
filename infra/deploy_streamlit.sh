#!/usr/bin/env bash
# Deploy latest code to the Streamlit EC2 instance via SSM.
# Usage: bash infra/deploy_streamlit.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Get instance ID from Terraform
INSTANCE_ID=$(cd "$SCRIPT_DIR" && terraform output -raw streamlit_instance_id)

echo "Deploying to instance $INSTANCE_ID..."

# Send command to pull latest, rebuild, and restart
COMMAND_ID=$(aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=[
    "cd /opt/streamlit-app",
    "git pull",
    "docker build -t streamlit-dashboard .",
    "docker stop streamlit || true",
    "docker rm streamlit || true",
    "docker run -d --name streamlit --restart always -p 8501:8501 streamlit-dashboard streamlit run streamlit_app/Home.py --server.port=8501 --server.address=0.0.0.0"
  ]' \
  --region eu-west-2 \
  --query "Command.CommandId" \
  --output text \
  --no-cli-pager)

echo "SSM command sent: $COMMAND_ID"
echo "Waiting for completion..."

aws ssm wait command-executed \
  --command-id "$COMMAND_ID" \
  --instance-id "$INSTANCE_ID" \
  --region eu-west-2 2>/dev/null || true

# Show result
STATUS=$(aws ssm get-command-invocation \
  --command-id "$COMMAND_ID" \
  --instance-id "$INSTANCE_ID" \
  --region eu-west-2 \
  --query "Status" \
  --output text \
  --no-cli-pager)

echo "Deploy status: $STATUS"

if [ "$STATUS" != "Success" ]; then
  echo "--- Output ---"
  aws ssm get-command-invocation \
    --command-id "$COMMAND_ID" \
    --instance-id "$INSTANCE_ID" \
    --region eu-west-2 \
    --query "StandardErrorContent" \
    --output text \
    --no-cli-pager
  exit 1
fi

echo "Deployed successfully."
