# =====================================================
# Phase 11-B: S3 Backup Infrastructure
# =====================================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket  = "terraform-state-552927148143"
    key     = "mailserver/s3-backup/terraform.tfstate"
    region  = "ap-northeast-1"
    encrypt = true
  }
}

# Provider: ap-northeast-1 (Tokyo) - Main region
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Mailserver"
      Phase       = "11-B"
      Purpose     = "S3 Backup Infrastructure"
      ManagedBy   = "Terraform"
      Environment = var.environment
    }
  }
}

# Provider: us-east-1 (for CloudWatch Billing Metrics)
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      Project     = "Mailserver"
      Phase       = "11-B"
      Purpose     = "S3 Backup Infrastructure"
      ManagedBy   = "Terraform"
      Environment = var.environment
    }
  }
}
