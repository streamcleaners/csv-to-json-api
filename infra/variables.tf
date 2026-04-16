variable "aws_region" {
  description = "AWS region to deploy to"
  type        = string
  default     = "eu-west-2"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "csv-to-json-api"
}

variable "key_name" {
  description = "EC2 key pair name for SSH access (leave empty to disable SSH)"
  type        = string
  default     = ""
}
