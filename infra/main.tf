terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# -----------------------------------------------------------------------------
# Lambda
# -----------------------------------------------------------------------------

resource "aws_iam_role" "lambda" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# -----------------------------------------------------------------------------
# S3 Data Bucket
# -----------------------------------------------------------------------------

resource "aws_s3_bucket" "data" {
  bucket        = "${var.project_name}-data-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

data "aws_caller_identity" "current" {}

resource "aws_iam_role_policy" "lambda_s3" {
  name = "${var.project_name}-lambda-s3"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket",
      ]
      Resource = [
        aws_s3_bucket.data.arn,
        "${aws_s3_bucket.data.arn}/*",
      ]
    }]
  })
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda_package"
  output_path = "${path.module}/../lambda_package.zip"
}

resource "aws_lambda_function" "api" {
  function_name    = "${var.project_name}-handler"
  role             = aws_iam_role.lambda.arn
  handler          = "app.handler.handler"
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 256
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      DATA_BUCKET = aws_s3_bucket.data.bucket
    }
  }
}

# -----------------------------------------------------------------------------
# API Gateway HTTP API (v2)
# -----------------------------------------------------------------------------

resource "aws_apigatewayv2_api" "api" {
  name          = var.project_name
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id             = aws_apigatewayv2_api.api.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

# -----------------------------------------------------------------------------
# Streamlit Dashboard (EC2)
# -----------------------------------------------------------------------------

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_security_group" "streamlit" {
  name        = "${var.project_name}-streamlit-sg"
  description = "Allow inbound traffic to Streamlit dashboard"

  ingress {
    description = "Streamlit"
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_iam_role" "streamlit" {
  name = "${var.project_name}-streamlit-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "streamlit_ssm" {
  role       = aws_iam_role.streamlit.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "streamlit" {
  name = "${var.project_name}-streamlit-profile"
  role = aws_iam_role.streamlit.name
}

resource "aws_instance" "streamlit" {
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = "t3.micro"
  vpc_security_group_ids      = [aws_security_group.streamlit.id]
  associate_public_ip_address = true
  iam_instance_profile        = aws_iam_instance_profile.streamlit.name
  user_data = <<-EOF
    #!/bin/bash
    set -euo pipefail
    exec > >(tee /var/log/streamlit-setup.log) 2>&1

    dnf install -y docker git amazon-ssm-agent
    systemctl enable amazon-ssm-agent
    systemctl start amazon-ssm-agent
    systemctl enable docker
    systemctl start docker

    git clone https://github.com/streamcleaners/csv-to-json-api.git /opt/streamlit-app
    cd /opt/streamlit-app

    docker build -t streamlit-dashboard .
    docker run -d \
      --name streamlit \
      --restart always \
      -p 8501:8501 \
      streamlit-dashboard \
      streamlit run streamlit_app/Home.py --server.port=8501 --server.address=0.0.0.0
  EOF

  key_name = var.key_name != "" ? var.key_name : null

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  tags = {
    Name = "${var.project_name}-streamlit"
  }
}
