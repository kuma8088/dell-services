# =====================================================
# Phase 11-B: IAM Configuration
# =====================================================

# IAM Role: Backup Uploader (write-only)
resource "aws_iam_role" "backup_uploader" {
  name = "mailserver-backup-uploader"
  max_session_duration = 7200  # 2 hours (for blog backup which takes >1h)

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_user.dell_system_admin.arn
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Purpose = "S3 Backup Upload"
  }
}

resource "aws_iam_role_policy" "backup_uploader" {
  name = "S3BackupUpload"
  role = aws_iam_role.backup_uploader.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowS3Upload"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectRetention",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.websystem_backup.arn,
          "${aws_s3_bucket.websystem_backup.arn}/*"
        ]
      },
      {
        Sid    = "DenyDeleteObject"
        Effect = "Deny"
        Action = [
          "s3:DeleteObject",
          "s3:DeleteObjectVersion"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM Role: Backup Admin (read-only)
resource "aws_iam_role" "backup_admin" {
  name = "mailserver-backup-admin"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_user.dell_system_admin.arn
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Purpose = "S3 Backup Restore"
  }
}

resource "aws_iam_role_policy" "backup_admin" {
  name = "S3BackupRestore"
  role = aws_iam_role.backup_admin.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowS3Read"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.websystem_backup.arn,
          "${aws_s3_bucket.websystem_backup.arn}/*"
        ]
      },
      {
        Sid    = "DenyDeleteObject"
        Effect = "Deny"
        Action = [
          "s3:DeleteObject",
          "s3:DeleteObjectVersion"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM User: dell-system-admin
resource "aws_iam_user" "dell_system_admin" {
  name = "dell-system-admin"

  tags = {
    Purpose = "Dell Mailserver Backup Operations"
  }
}

resource "aws_iam_user_policy" "dell_assume_role" {
  name = "AssumeBackupRoles"
  user = aws_iam_user.dell_system_admin.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sts:AssumeRole"
        Resource = [
          aws_iam_role.backup_uploader.arn,
          aws_iam_role.backup_admin.arn
        ]
      }
    ]
  })
}
