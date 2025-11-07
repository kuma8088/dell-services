# =====================================================
# Phase 11-B: Outputs
# =====================================================

output "s3_bucket_name" {
  description = "S3 bucket name for backups"
  value       = aws_s3_bucket.mailserver_backup.id
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.mailserver_backup.arn
}

output "backup_uploader_role_arn" {
  description = "IAM role ARN for backup uploads"
  value       = aws_iam_role.backup_uploader.arn
}

output "backup_admin_role_arn" {
  description = "IAM role ARN for backup restores"
  value       = aws_iam_role.backup_admin.arn
}

output "iam_user_name" {
  description = "IAM user name for Dell operations"
  value       = aws_iam_user.dell_system_admin.name
}

output "sns_topic_arn" {
  description = "SNS topic ARN for alerts"
  value       = aws_sns_topic.backup_alerts.arn
}
