# =====================================================
# Phase 11-B: S3 Backup Bucket
# =====================================================

resource "aws_s3_bucket" "websystem_backup" {
  bucket = var.backup_bucket_name

  tags = {
    Purpose = "Web System S3 Backup - Mail and Blog"
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "websystem_backup" {
  bucket = aws_s3_bucket.websystem_backup.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "websystem_backup" {
  bucket = aws_s3_bucket.websystem_backup.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
