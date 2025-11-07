# =====================================================
# Phase 11-B: S3 Backup Bucket
# =====================================================

resource "aws_s3_bucket" "mailserver_backup" {
  bucket = "mailserver-backup-552927148143"

  # Object Lock requires versioning (enabled separately)
  object_lock_enabled = true

  tags = {
    Purpose = "Mailserver S3 Backup with Object Lock"
  }
}

# Versioning (required for Object Lock)
resource "aws_s3_bucket_versioning" "mailserver_backup" {
  bucket = aws_s3_bucket.mailserver_backup.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Object Lock Configuration (COMPLIANCE mode)
resource "aws_s3_bucket_object_lock_configuration" "mailserver_backup" {
  bucket = aws_s3_bucket.mailserver_backup.id

  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = var.object_lock_days
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "mailserver_backup" {
  bucket = aws_s3_bucket.mailserver_backup.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "mailserver_backup" {
  bucket = aws_s3_bucket.mailserver_backup.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
