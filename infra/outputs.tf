output "api_url" {
  description = "API endpoint URL"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.api.function_name
}

output "streamlit_url" {
  description = "Streamlit dashboard URL"
  value       = "http://${aws_eip.streamlit.public_ip}:8501"
}

output "streamlit_instance_id" {
  description = "Streamlit EC2 instance ID"
  value       = aws_instance.streamlit.id
}

output "data_bucket" {
  description = "S3 bucket for CSV data"
  value       = aws_s3_bucket.data.bucket
}
