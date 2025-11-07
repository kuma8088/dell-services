# =====================================================
# Phase 11-B: CloudWatch Alarms and SNS
# =====================================================

# CloudWatch Alarms for S3 Cost Monitoring
# NOTE: AWS/Billing metrics are only available in us-east-1
resource "aws_cloudwatch_metric_alarm" "s3_cost_warning" {
  provider = aws.us_east_1

  alarm_name          = "mailserver-s3-backup-cost-warning"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = 86400  # 1 day
  statistic           = "Maximum"
  threshold           = 10  # 10円/月（現行データ量想定値）
  alarm_description   = "S3 backup cost exceeded expected threshold (10 JPY/month)"
  alarm_actions       = [aws_sns_topic.backup_alerts.arn]

  dimensions = {
    ServiceName = "AmazonS3"
    Currency    = "JPY"
  }

  tags = {
    Severity = "WARNING"
    Purpose  = "Cost Monitoring - Expected Threshold"
  }
}

resource "aws_cloudwatch_metric_alarm" "s3_cost_critical" {
  provider = aws.us_east_1

  alarm_name          = "mailserver-s3-backup-cost-critical"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = 86400  # 1 day
  statistic           = "Maximum"
  threshold           = 100  # 100円/月（異常検知閾値）
  alarm_description   = "S3 backup cost critically high - investigation required (100 JPY/month)"
  alarm_actions       = [aws_sns_topic.backup_alerts.arn]

  dimensions = {
    ServiceName = "AmazonS3"
    Currency    = "JPY"
  }

  tags = {
    Severity = "CRITICAL"
    Purpose  = "Cost Monitoring - Abnormal Activity Detection"
  }
}

# SNS Topic for Alerts
resource "aws_sns_topic" "backup_alerts" {
  provider = aws.us_east_1

  name = "mailserver-s3-backup-alerts"

  tags = {
    Purpose = "S3 Backup Alert Notifications"
  }
}

resource "aws_sns_topic_subscription" "backup_alerts_email" {
  provider = aws.us_east_1

  topic_arn = aws_sns_topic.backup_alerts.arn
  protocol  = "email"
  endpoint  = var.admin_email
}
