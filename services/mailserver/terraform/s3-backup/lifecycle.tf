# =====================================================
# Phase 11-B: S3 Lifecycle Configuration
# =====================================================

resource "aws_s3_bucket_lifecycle_configuration" "mailserver_backup" {
  bucket = aws_s3_bucket.mailserver_backup.id

  rule {
    id     = "daily-backups-lifecycle"
    status = "Enabled"

    filter {
      prefix = "daily/"
    }

    transition {
      days          = var.retention_days
      storage_class = "GLACIER"
    }

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}
