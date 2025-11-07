# =====================================================
# Phase 11-B: Variables
# =====================================================

variable "aws_region" {
  description = "AWS region for S3 backup bucket"
  type        = string
  default     = "ap-northeast-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "admin_email" {
  description = "Administrator email for alerts"
  type        = string
}

variable "retention_days" {
  description = "Days to retain backups in S3 Standard before moving to Glacier"
  type        = number
  default     = 30
}

variable "object_lock_days" {
  description = "Days to retain backups with Object Lock (ransomware protection)"
  type        = number
  default     = 30
}
