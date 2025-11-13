# =====================================================
# Phase 11-B: S3 Lifecycle Configuration
# =====================================================

resource "aws_s3_bucket_lifecycle_configuration" "websystem_backup" {
  bucket = aws_s3_bucket.websystem_backup.id

  rule {
    id     = "daily-backups-lifecycle"
    status = "Enabled"

    filter {
      prefix = "daily/"
    }

    # 7日後に削除（災害時バックアップ用、必要なら延長可能）
    expiration {
      days = 7
    }
  }
}
