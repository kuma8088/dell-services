# ============================================================================
# Terraform Variables
# ============================================================================
# Purpose: Centralized definition of input variables for the mailserver stack.
# ============================================================================

variable "aws_region" {
  description = "AWS region for mail server infrastructure"
  type        = string
  default     = "ap-northeast-1"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "production"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_1a_cidr" {
  description = "CIDR block for public subnet in ap-northeast-1a"
  type        = string
  default     = "10.0.1.0/24"
}

variable "public_subnet_1c_cidr" {
  description = "CIDR block for public subnet in ap-northeast-1c"
  type        = string
  default     = "10.0.2.0/24"
}

variable "cluster_name" {
  description = "ECS cluster name"
  type        = string
  default     = "mailserver-cluster"
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention period in days"
  type        = number
  default     = 30
}
