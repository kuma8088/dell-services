# Phase 11-B: S3バックアップシステム実装ガイド

**ドキュメントバージョン**: 1.2
**最終更新日**: 2025-11-07
**対象フェーズ**: Phase 11-B（S3オフサイトバックアップ）
**前提フェーズ**: Phase 10（ローカルバックアップ）完了

---

## 目次

1. [概要](#1-概要)
2. [事前準備](#2-事前準備)
3. [Terraform実装](#3-terraform実装)
4. [マルウェアスキャン環境構築](#4-マルウェアスキャン環境構築)
5. [スクリプト実装](#5-スクリプト実装)
6. [cron設定](#6-cron設定)
7. [動作確認](#7-動作確認)
8. [トラブルシューティング](#8-トラブルシューティング)

---

## 1. 概要

### 1.1 実装するもの

Phase 11-Bでは以下を実装します：

1. **Terraform インフラ** (S3, IAM, CloudWatch, SNS)
2. **マルウェアスキャン環境** (Host ClamAV + rkhunter)
3. **バックアップスクリプト** (4つのBashスクリプト)
4. **cron自動実行** (日次・週次スケジュール)

### 1.2 実装順序

```
Phase 10（ローカルバックアップ）
  ↓
1. 事前準備（AWS CLI, Terraform, 権限確認）
  ↓
2. Terraform デプロイ（S3, IAM, CloudWatch）
  ↓
3. マルウェアスキャン環境構築（ClamAV, rkhunter）
  ↓
4. スクリプト実装（TDD開発）
  ↓
5. cron設定
  ↓
6. 動作確認・テスト
```

### 1.3 所要時間

| タスク | 所要時間 | 難易度 |
|-------|---------|-------|
| 事前準備 | 30分 | 低 |
| Terraform デプロイ | 1時間 | 中 |
| マルウェアスキャン構築 | 1時間 | 中 |
| スクリプト実装 | 4-6時間 | 高 |
| cron設定 | 30分 | 低 |
| 動作確認 | 1-2時間 | 中 |
| **合計** | **8-11時間** | - |

---

## 2. 事前準備

### 2.1 前提条件確認

**Phase 10（ローカルバックアップ）が完了していること**:

```bash
# 確認1: バックアップスクリプトが存在
ls -l /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-mailserver.sh

# 確認2: 最近のバックアップが存在
ls -l /mnt/backup-hdd/mailserver/daily/

# 確認3: バックアップが正常動作
./services/mailserver/scripts/backup-mailserver.sh --daily
# → 成功すること
```

### 2.2 AWS CLI設定

#### 2.2.1 AWS CLIインストール確認

```bash
aws --version
# → aws-cli/2.x.x 以上
```

インストールされていない場合:

```bash
# Rocky Linux 9.6
sudo dnf install -y aws-cli

# または最新版をインストール
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

#### 2.2.2 AWS認証情報設定

```bash
aws configure --profile mailserver-backup
```

入力内容:
```
AWS Access Key ID: AKIA...
AWS Secret Access Key: ...
Default region name: ap-northeast-1
Default output format: json
```

**重要**: このプロファイルは後でIAMロールに切り替えますが、初期セットアップ時は管理者権限が必要です。

#### 2.2.3 マルチリージョン対応確認

```bash
# ap-northeast-1 でのアクセス確認
aws s3 ls --profile mailserver-backup --region ap-northeast-1

# us-east-1 でのアクセス確認（Billing メトリクス用）
aws cloudwatch list-metrics --namespace AWS/Billing \
  --profile mailserver-backup --region us-east-1
```

両方のリージョンで動作すればOK（IAMはグローバルサービスなので同一認証情報で動作）。

### 2.3 Terraform環境構築

#### 2.3.1 Terraformインストール確認

```bash
terraform version
# → Terraform v1.0 以上
```

インストールされていない場合:

```bash
# Rocky Linux 9.6
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
sudo dnf install -y terraform
```

#### 2.3.2 Terraform State用S3バケット作成

```bash
# アカウントID取得
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --profile mailserver-backup)

# State用バケット作成（初回のみ）
aws s3 mb "s3://terraform-state-${AWS_ACCOUNT_ID}" \
  --region ap-northeast-1 \
  --profile mailserver-backup

# バージョニング有効化
aws s3api put-bucket-versioning \
  --bucket "terraform-state-${AWS_ACCOUNT_ID}" \
  --versioning-configuration Status=Enabled \
  --region ap-northeast-1 \
  --profile mailserver-backup
```

### 2.4 必要な権限確認

Terraform実行に必要な最小権限:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:PutBucketVersioning",
        "s3:PutBucketObjectLockConfiguration",
        "s3:PutBucketPolicy",
        "s3:PutBucketPublicAccessBlock",
        "s3:PutEncryptionConfiguration",
        "s3:PutLifecycleConfiguration",
        "iam:CreateRole",
        "iam:CreatePolicy",
        "iam:CreateUser",
        "iam:CreateAccessKey",
        "iam:AttachRolePolicy",
        "iam:AttachUserPolicy",
        "cloudwatch:PutMetricAlarm",
        "sns:CreateTopic",
        "sns:Subscribe"
      ],
      "Resource": "*"
    }
  ]
}
```

権限確認:

```bash
# S3作成権限確認
aws s3 mb s3://test-permissions-check-${AWS_ACCOUNT_ID} \
  --region ap-northeast-1 \
  --profile mailserver-backup

# 確認できたら削除
aws s3 rb s3://test-permissions-check-${AWS_ACCOUNT_ID} \
  --profile mailserver-backup
```

### 2.5 環境変数設定

#### 2.5.1 Terraform実行用環境変数

```bash
# ~/.bashrc または ~/.bash_profile に追加（対話シェル用）
cat >> ~/.bashrc <<'EOF'

# Phase 11-B: Terraform Configuration
export AWS_PROFILE=mailserver-backup
export AWS_DEFAULT_REGION=ap-northeast-1
export TF_VAR_admin_email="your-email@example.com"  # 実際のメールアドレスに変更
EOF

source ~/.bashrc
```

**重要**: `TF_VAR_admin_email` は実際の管理者メールアドレスに変更してください。

#### 2.5.2 スクリプト用設定ファイル

**重要**: cronは非対話シェルのため `~/.bashrc` を読み込みません。スクリプト用の設定ファイルを別途作成します。

```bash
# 設定ファイル作成
sudo mkdir -p /etc/mailserver-backup
sudo tee /etc/mailserver-backup/config <<EOF
# Phase 11-B: Backup Script Configuration

# メール通知設定
ADMIN_EMAIL="your-email@example.com"  # 実際のメールアドレスに変更

# AWS設定（cron実行時に必要）
AWS_PROFILE=mailserver-backup-uploader
AWS_DEFAULT_REGION=ap-northeast-1
EOF

# パーミッション設定（管理者のみ読み取り可）
sudo chmod 600 /etc/mailserver-backup/config
sudo chown system-admin:system-admin /etc/mailserver-backup/config
```

**重要**: `ADMIN_EMAIL` には実際の管理者メールアドレスを設定してください。

**説明**: AWS_PROFILE と AWS_DEFAULT_REGION をシステム全体の設定ファイルで管理することで、cron 実行時と手動実行時の動作を一貫させます。

---

## 3. Terraform実装

### 3.1 ディレクトリ構造作成

```bash
cd /opt/onprem-infra-system/project-root-infra

# Terraformディレクトリ作成
mkdir -p services/mailserver/terraform/s3-backup
cd services/mailserver/terraform/s3-backup
```

### 3.2 Terraformファイル作成

#### 3.2.1 main.tf

```bash
cat > main.tf <<'EOF'
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    # 実際のACCOUNT-IDに置き換え
    bucket = "terraform-state-ACCOUNT-ID"
    key    = "mailserver/s3-backup/terraform.tfstate"
    region = "ap-northeast-1"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Mailserver"
      Component   = "S3-Backup"
      ManagedBy   = "Terraform"
      Environment = var.environment
    }
  }
}

# CloudWatch Billing メトリクスは us-east-1 でのみ利用可能
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      Project     = "Mailserver"
      Component   = "S3-Backup"
      ManagedBy   = "Terraform"
      Environment = var.environment
    }
  }
}

data "aws_caller_identity" "current" {}
EOF
```

**重要**: `terraform-state-ACCOUNT-ID` を実際のAWSアカウントIDに置き換えてください。

```bash
# アカウントID取得
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# main.tf を置換
sed -i "s/ACCOUNT-ID/${AWS_ACCOUNT_ID}/g" main.tf
```

#### 3.2.2 variables.tf

```bash
cat > variables.tf <<'EOF'
variable "aws_region" {
  description = "AWS region for S3 bucket"
  type        = string
  default     = "ap-northeast-1"
}

variable "environment" {
  description = "Environment name (production, staging, etc.)"
  type        = string
  default     = "production"
}

variable "admin_email" {
  description = "Email address for alert notifications"
  type        = string
  sensitive   = true
}

variable "retention_days" {
  description = "Number of days to retain backups in STANDARD storage"
  type        = number
  default     = 30
}

variable "object_lock_days" {
  description = "Number of days for Object Lock COMPLIANCE mode"
  type        = number
  default     = 30
}
EOF
```

#### 3.2.3 s3.tf

```bash
cat > s3.tf <<'EOF'
resource "aws_s3_bucket" "mailserver_backup" {
  bucket = "mailserver-backup-${data.aws_caller_identity.current.account_id}"

  # Object Lock は作成時に有効化が必須（後付け不可）
  object_lock_enabled = true

  tags = {
    Name        = "Mailserver Backup"
    Purpose     = "Ransomware Protection"
    DataType    = "State Data"
  }
}

resource "aws_s3_bucket_versioning" "mailserver_backup" {
  bucket = aws_s3_bucket.mailserver_backup.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "mailserver_backup" {
  bucket = aws_s3_bucket.mailserver_backup.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_object_lock_configuration" "mailserver_backup" {
  bucket = aws_s3_bucket.mailserver_backup.id

  # Object Lock には Versioning が必須
  depends_on = [aws_s3_bucket_versioning.mailserver_backup]

  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = var.object_lock_days
    }
  }
}

resource "aws_s3_bucket_public_access_block" "mailserver_backup" {
  bucket = aws_s3_bucket.mailserver_backup.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "mailserver_backup" {
  bucket = aws_s3_bucket.mailserver_backup.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyInsecureTransport"
        Effect = "Deny"
        Principal = "*"
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.mailserver_backup.arn,
          "${aws_s3_bucket.mailserver_backup.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}
EOF
```

#### 3.2.4 iam.tf

```bash
cat > iam.tf <<'EOF'
# IAM Role: Backup Uploader
resource "aws_iam_role" "backup_uploader" {
  name = "mailserver-backup-uploader"

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
          aws_s3_bucket.mailserver_backup.arn,
          "${aws_s3_bucket.mailserver_backup.arn}/daily/*"
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
          aws_s3_bucket.mailserver_backup.arn,
          "${aws_s3_bucket.mailserver_backup.arn}/*"
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
EOF
```

#### 3.2.5 lifecycle.tf

```bash
cat > lifecycle.tf <<'EOF'
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
EOF
```

#### 3.2.6 cloudwatch.tf

```bash
cat > cloudwatch.tf <<'EOF'
# CloudWatch Alarms for S3 Cost Monitoring
# NOTE: AWS/Billing メトリクスは us-east-1 でのみ利用可能
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
EOF
```

#### 3.2.7 outputs.tf

```bash
cat > outputs.tf <<'EOF'
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
EOF
```

#### 3.2.8 .gitignore

```bash
cat > .gitignore <<'EOF'
# Terraform
.terraform/
*.tfstate
*.tfstate.backup
.terraform.lock.hcl

# Variables (機密情報を含む可能性)
terraform.tfvars
*.auto.tfvars
EOF
```

### 3.3 Terraform デプロイ

#### 3.3.1 初期化

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/terraform/s3-backup

terraform init
```

出力例:
```
Initializing the backend...
Initializing provider plugins...
Terraform has been successfully initialized!
```

#### 3.3.2 プラン確認

```bash
terraform plan
```

以下のリソースが作成される予定であることを確認:
- `aws_s3_bucket.mailserver_backup`
- `aws_s3_bucket_versioning.mailserver_backup`
- `aws_s3_bucket_object_lock_configuration.mailserver_backup`
- `aws_iam_role.backup_uploader`
- `aws_iam_role.backup_admin`
- `aws_iam_user.dell_system_admin`
- `aws_cloudwatch_metric_alarm.s3_cost_warning` (us-east-1)
- `aws_cloudwatch_metric_alarm.s3_cost_critical` (us-east-1)
- `aws_sns_topic.backup_alerts` (us-east-1)
- `aws_sns_topic_subscription.backup_alerts_email` (us-east-1)

#### 3.3.3 適用

```bash
terraform apply
```

確認メッセージで `yes` を入力。

#### 3.3.4 SNS確認メール対応（重要）

Terraform apply 完了後、`var.admin_email` に指定したメールアドレス宛にAWSから確認メールが届きます。

**件名**: "AWS Notification - Subscription Confirmation"

**手順**:
1. メール内の "Confirm subscription" リンクをクリック
2. ブラウザで確認ページが開く
3. "Subscription confirmed!" と表示されればOK

**確認**:
```bash
aws sns list-subscriptions-by-topic \
  --topic-arn $(terraform output -raw sns_topic_arn) \
  --region us-east-1 \
  --profile mailserver-backup
```

出力で `"SubscriptionArn"` が `arn:aws:sns:...` となっていればOK（`PendingConfirmation` でないこと）。

#### 3.3.5 IAMユーザーのアクセスキー作成

```bash
# アクセスキー作成
aws iam create-access-key --user-name dell-system-admin \
  --profile mailserver-backup

# 出力例:
# {
#   "AccessKey": {
#     "AccessKeyId": "AKIA...",
#     "SecretAccessKey": "...",
#     "Status": "Active"
#   }
# }
```

**重要**: `AccessKeyId` と `SecretAccessKey` を安全に保存してください。

#### 3.3.6 AWS CLI プロファイル更新

```bash
# 新しいプロファイル作成（IAMユーザー用）
aws configure --profile mailserver-backup-dell

# 入力内容:
# AWS Access Key ID: AKIA... (上記で作成したキー)
# AWS Secret Access Key: ... (上記で作成したシークレット)
# Default region name: ap-northeast-1
# Default output format: json
```

#### 3.3.7 IAMロール設定

~/.aws/config に以下を追加:

```bash
cat >> ~/.aws/config <<'EOF'

[profile mailserver-backup-uploader]
role_arn = <backup_uploader_role_arn>
source_profile = mailserver-backup-dell
region = ap-northeast-1

[profile mailserver-backup-admin]
role_arn = <backup_admin_role_arn>
source_profile = mailserver-backup-dell
region = ap-northeast-1
EOF
```

**置換**:
```bash
# Terraform output から Role ARN 取得
UPLOADER_ARN=$(terraform output -raw backup_uploader_role_arn)
ADMIN_ARN=$(terraform output -raw backup_admin_role_arn)

# config を置換
sed -i "s|<backup_uploader_role_arn>|${UPLOADER_ARN}|g" ~/.aws/config
sed -i "s|<backup_admin_role_arn>|${ADMIN_ARN}|g" ~/.aws/config
```

#### 3.3.8 動作確認

```bash
# アップロード権限確認
aws s3 ls s3://$(terraform output -raw s3_bucket_name)/ \
  --profile mailserver-backup-uploader

# リストア権限確認
aws s3 ls s3://$(terraform output -raw s3_bucket_name)/ \
  --profile mailserver-backup-admin
```

両方で正常にリストが表示されればOK。

---

## 4. マルウェアスキャン環境構築

### 4.1 Host ClamAV インストール

#### 4.1.1 ClamAVインストール

```bash
# EPEL有効化（Rocky Linux 9.6）
sudo dnf install -y epel-release

# ClamAVインストール
sudo dnf install -y clamav clamav-update clamd
```

#### 4.1.2 ウイルス定義更新

```bash
# freshclam設定
sudo vim /etc/freshclam.conf
# → "Example" 行をコメントアウト

# 初回ウイルス定義ダウンロード
sudo freshclam
```

出力例:
```
ClamAV update process started at ...
Downloading main.cvd [100%]
...
Database updated (xxx signatures)
```

#### 4.1.3 clamd設定

```bash
# clamd設定ファイル編集
sudo vim /etc/clamd.d/scan.conf
```

以下を設定:
```
# "Example" 行をコメントアウト
#Example

# TCP socket有効化（オプション）
TCPSocket 3310
TCPAddr 127.0.0.1

# ログ設定
LogFile /var/log/clamd.scan
LogTime yes
LogSyslog yes
```

#### 4.1.4 clamd起動

```bash
# サービス有効化・起動
sudo systemctl enable clamd@scan
sudo systemctl start clamd@scan

# 状態確認
sudo systemctl status clamd@scan
```

#### 4.1.5 スキャンテスト

```bash
# EICAR テストファイル作成
echo 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' > /tmp/eicar.txt

# スキャン実行
clamscan /tmp/eicar.txt

# 出力例:
# /tmp/eicar.txt: Eicar-Test-Signature FOUND
# ...
# Infected files: 1

# テストファイル削除
rm /tmp/eicar.txt
```

### 4.2 rkhunter インストール

#### 4.2.1 rkhunterインストール

```bash
# EPELから インストール
sudo dnf install -y rkhunter
```

#### 4.2.2 rkhunter初期設定

```bash
# 設定ファイル編集
sudo vim /etc/rkhunter.conf
```

以下を設定:
```conf
# メール通知設定（オプション）
MAIL-ON-WARNING=root

# ログ設定
LOGFILE=/var/log/rkhunter.log

# 自動更新
UPDATE_MIRRORS=1
MIRRORS_MODE=0
WEB_CMD=""
```

#### 4.2.3 rkhunter初期化

```bash
# データベース更新
sudo rkhunter --update

# プロパティ初期設定
sudo rkhunter --propupd
```

#### 4.2.4 rkhunterテスト実行

```bash
# システムスキャン実行
sudo rkhunter --check --skip-keypress

# ログ確認
sudo tail -50 /var/log/rkhunter.log
```

警告が出る場合は既知の誤検出かを確認。

### 4.3 隔離ディレクトリ作成

```bash
# 隔離ディレクトリ作成
sudo mkdir -p /var/quarantine
sudo chmod 700 /var/quarantine

# 所有者設定
sudo chown system-admin:system-admin /var/quarantine
```

---

## 5. スクリプト実装

### 5.1 スクリプト配置先

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts
```

### 5.2 共通設定ファイル

#### 5.2.1 backup-config.sh

```bash
cat > backup-config.sh <<'EOF'
#!/bin/bash
# backup-config.sh - 共通設定ファイル

# 外部設定ファイル読み込み（cron対応）
if [ -f /etc/mailserver-backup/config ]; then
    source /etc/mailserver-backup/config
else
    echo "ERROR: /etc/mailserver-backup/config not found" >&2
    exit 1
fi

# AWS設定を export（/etc/mailserver-backup/config から読み込み済み）
export AWS_PROFILE
export AWS_DEFAULT_REGION
export S3_BUCKET="mailserver-backup-$(aws sts get-caller-identity --query Account --output text)"

# バックアップディレクトリ
export DAILY_BACKUP_DIR="/mnt/backup-hdd/mailserver/daily"
export WEEKLY_BACKUP_DIR="/mnt/backup-hdd/mailserver/weekly"

# ログ設定
export LOG_DIR="/var/log/mailserver-backup"
export LOG_FILE="${LOG_DIR}/s3-backup.log"

# ロックファイル
export LOCK_FILE="/var/run/mailserver-s3-backup.lock"

# タイムアウト設定
export UPLOAD_TIMEOUT=1800  # 30分

# ログ関数
log() {
    local level="$1"
    shift
    local message="$*"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${level}] ${message}" | tee -a "${LOG_FILE}"
}

# ロックファイルチェック
check_lock_file() {
    if [ -f "${LOCK_FILE}" ]; then
        log "ERROR" "Another instance is running (lock file exists)"
        exit 1
    fi
    touch "${LOCK_FILE}"
    trap "rm -f ${LOCK_FILE}" EXIT
}
EOF

chmod +x backup-config.sh
```

### 5.3 backup-to-s3.sh 実装

```bash
cat > backup-to-s3.sh <<'EOF'
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/backup-config.sh"

# ログディレクトリ作成
mkdir -p "${LOG_DIR}"

# 初期化
initialize() {
    log "INFO" "=== S3 Backup Upload Started ==="
    check_lock_file

    # AWS CLI確認
    if ! command -v aws &> /dev/null; then
        log "ERROR" "AWS CLI not found"
        exit 1
    fi

    # IAM認証確認
    if ! aws sts get-caller-identity --profile "${AWS_PROFILE}" &> /dev/null; then
        log "ERROR" "AWS authentication failed"
        exit 1
    fi

    log "INFO" "Initialization completed"
}

# バックアップ検証
validate_local_backup() {
    local backup_date=$(date -d "yesterday" '+%Y-%m-%d')
    local backup_dir="${DAILY_BACKUP_DIR}/${backup_date}"

    log "INFO" "Validating local backup: ${backup_dir}"

    if [ ! -d "${backup_dir}" ]; then
        log "ERROR" "Backup directory not found: ${backup_dir}"
        return 1
    fi

    # チェックサム検証
    cd "${backup_dir}"
    if [ -f checksums.sha256 ]; then
        if sha256sum -c checksums.sha256 > /dev/null 2>&1; then
            log "INFO" "Checksum verification passed"
        else
            log "ERROR" "Checksum verification failed"
            return 1
        fi
    else
        log "WARNING" "checksums.sha256 not found, skipping verification"
    fi

    return 0
}

# S3アップロード
upload_to_s3() {
    local backup_date=$(date -d "yesterday" '+%Y-%m-%d')
    local source_dir="${DAILY_BACKUP_DIR}/${backup_date}"
    local s3_dest="s3://${S3_BUCKET}/daily/${backup_date}/"

    log "INFO" "Uploading to S3: ${s3_dest}"

    # リトライロジック
    local max_attempts=3
    local attempt=1

    while [ ${attempt} -le ${max_attempts} ]; do
        log "INFO" "Upload attempt ${attempt}/${max_attempts}"

        if timeout ${UPLOAD_TIMEOUT} aws s3 sync "${source_dir}/" "${s3_dest}" \
            --profile "${AWS_PROFILE}" \
            --sse AES256 \
            --storage-class STANDARD \
            --no-progress \
            2>&1 | tee -a "${LOG_FILE}"; then

            log "INFO" "Upload successful"
            return 0
        else
            local exit_code=$?
            log "ERROR" "Upload failed (attempt ${attempt}/${max_attempts}), exit code: ${exit_code}"

            if [ ${attempt} -lt ${max_attempts} ]; then
                local wait_time=$((2 ** attempt))
                log "INFO" "Waiting ${wait_time} seconds before retry..."
                sleep ${wait_time}
            fi
        fi

        attempt=$((attempt + 1))
    done

    log "ERROR" "Upload failed after ${max_attempts} attempts"
    send_alert "CRITICAL" "S3 upload failed after ${max_attempts} attempts for ${backup_date}"
    return 1
}

# アップロード検証
verify_s3_upload() {
    local backup_date=$(date -d "yesterday" '+%Y-%m-%d')
    local s3_path="s3://${S3_BUCKET}/daily/${backup_date}/"

    log "INFO" "Verifying S3 upload: ${s3_path}"

    # オブジェクト数確認
    local s3_count=$(aws s3 ls "${s3_path}" --recursive --profile "${AWS_PROFILE}" | wc -l)
    local local_count=$(find "${DAILY_BACKUP_DIR}/${backup_date}" -type f | wc -l)

    if [ ${s3_count} -ne ${local_count} ]; then
        log "ERROR" "File count mismatch: S3=${s3_count}, Local=${local_count}"
        send_alert "ERROR" "S3 upload verification failed: file count mismatch"
        return 1
    fi

    log "INFO" "Verification successful: ${s3_count} files uploaded"
    return 0
}

# アラート送信
send_alert() {
    local severity="$1"
    local message="$2"

    local subject="[${severity}] Mailserver S3 Backup Alert"

    if [ -n "${ADMIN_EMAIL}" ]; then
        echo "${message}" | mail -s "${subject}" "${ADMIN_EMAIL}" || true
    fi

    log "${severity}" "${message}"
}

# メイン処理
main() {
    initialize || exit 1
    validate_local_backup || exit 1
    upload_to_s3 || exit 1
    verify_s3_upload || exit 1

    log "INFO" "=== S3 Backup Upload Completed ==="
}

main "$@"
EOF

chmod +x backup-to-s3.sh
```

### 5.4 restore-from-s3.sh 実装

```bash
cat > restore-from-s3.sh <<'EOF'
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/backup-config.sh"

# リストア用のプロファイル（読み取り専用）
# 注: export しない（子プロセスに継承させない）
# scan-restored-data.sh などの子スクリプトには AWS_PROFILE (uploader) が渡される
readonly RESTORE_PROFILE=mailserver-backup-admin

# 引数解析
BACKUP_DATE=""
COMPONENT="all"

while [[ $# -gt 0 ]]; do
    case $1 in
        --date)
            BACKUP_DATE="$2"
            shift 2
            ;;
        --component)
            COMPONENT="$2"
            shift 2
            ;;
        *)
            echo "Usage: $0 --date YYYY-MM-DD [--component all|mail|mysql|config]"
            exit 1
            ;;
    esac
done

# 最新バックアップ日付取得
get_latest_backup_date() {
    aws s3 ls "s3://${S3_BUCKET}/daily/" --profile "${RESTORE_PROFILE}" \
        | awk '{print $2}' \
        | sed 's#/##g' \
        | sort -r \
        | head -n 1
}

# S3ダウンロード
download_from_s3() {
    local date="$1"
    local restore_dir="/tmp/s3-restore-$$/​${date}"
    mkdir -p "${restore_dir}"

    log "INFO" "Downloading from S3: ${date}"

    aws s3 sync "s3://${S3_BUCKET}/daily/${date}/" "${restore_dir}/" \
        --profile "${RESTORE_PROFILE}" \
        2>&1 | tee -a "${LOG_FILE}"

    echo "${restore_dir}"
}

# チェックサム検証
verify_checksums() {
    local restore_dir="$1"

    log "INFO" "Verifying checksums"

    cd "${restore_dir}"
    if [ -f checksums.sha256 ]; then
        if sha256sum -c checksums.sha256; then
            log "INFO" "Checksum verification passed"
            return 0
        else
            log "ERROR" "Checksum verification failed"
            return 1
        fi
    else
        log "WARNING" "checksums.sha256 not found"
        return 0
    fi
}

# マルウェアスキャン
scan_backup() {
    local restore_dir="$1"

    log "INFO" "Scanning backup for malware"

    if "${SCRIPT_DIR}/scan-restored-data.sh" --source "${restore_dir}"; then
        log "INFO" "Malware scan passed"
        return 0
    else
        log "ERROR" "Malware detected in backup"
        return 1
    fi
}

# リストア実行
restore_data() {
    local restore_dir="$1"
    local component="$2"

    log "INFO" "Restoring data from: ${restore_dir}"

    "${SCRIPT_DIR}/restore-mailserver.sh" \
        --from "${restore_dir}" \
        --component "${component}"
}

# メイン処理
main() {
    log "INFO" "=== S3 Restore Started ==="

    # 日付未指定なら最新を取得
    if [ -z "${BACKUP_DATE}" ]; then
        BACKUP_DATE=$(get_latest_backup_date)
        log "INFO" "Using latest backup: ${BACKUP_DATE}"
    fi

    # S3ダウンロード
    restore_dir=$(download_from_s3 "${BACKUP_DATE}")

    # チェックサム検証
    if ! verify_checksums "${restore_dir}"; then
        log "ERROR" "Verification failed, aborting restore"
        rm -rf "${restore_dir}"
        exit 1
    fi

    # マルウェアスキャン
    if ! scan_backup "${restore_dir}"; then
        log "WARNING" "Malware detected, trying previous day..."
        rm -rf "${restore_dir}"

        # 前日のバックアップにフォールバック
        local previous_date=$(date -d "${BACKUP_DATE} -1 day" '+%Y-%m-%d')
        restore_dir=$(download_from_s3 "${previous_date}")

        if ! scan_backup "${restore_dir}"; then
            log "ERROR" "Malware detected in previous backup too, aborting"
            rm -rf "${restore_dir}"
            exit 1
        fi
    fi

    # リストア実行
    restore_data "${restore_dir}" "${COMPONENT}"

    # クリーンアップ
    rm -rf "${restore_dir}"

    log "INFO" "=== S3 Restore Completed ==="
}

main "$@"
EOF

chmod +x restore-from-s3.sh
```

### 5.5 scan-mailserver.sh 実装

```bash
cat > scan-mailserver.sh <<'EOF'
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/backup-config.sh"

# スキャンタイプ
SCAN_TYPE="daily"

if [ $# -gt 0 ]; then
    SCAN_TYPE="$1"
fi

case "${SCAN_TYPE}" in
    --daily|daily)
        SCAN_MODE="daily"
        ;;
    --weekly|weekly)
        SCAN_MODE="weekly"
        ;;
    *)
        echo "Usage: $0 [--daily|--weekly]"
        exit 1
        ;;
esac

# 隔離ディレクトリ
QUARANTINE_DIR="/var/quarantine"
mkdir -p "${QUARANTINE_DIR}"

# 日次スキャン
daily_scan() {
    log "INFO" "=== Daily Malware Scan Started ==="

    # 1. Docker ClamAV でメールデータスキャン
    log "INFO" "Scanning mail data with Docker ClamAV"
    docker exec mailserver-clamav clamscan -r /var/mail/vmail/ \
        --infected \
        --move=/var/quarantine/ \
        --log=/var/log/clamav/daily-scan.log \
        2>&1 | tee -a "${LOG_FILE}" || true

    # 2. Host ClamAV でメールデータディレクトリスキャン
    log "INFO" "Scanning mail data with Host ClamAV"
    clamscan -r /opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail/ \
        --infected \
        --log=/var/log/clamav/host-daily-scan.log \
        2>&1 | tee -a "${LOG_FILE}" || true

    log "INFO" "=== Daily Malware Scan Completed ==="
}

# 週次スキャン
weekly_scan() {
    log "INFO" "=== Weekly Malware Scan Started ==="

    # 日次スキャン実行
    daily_scan

    # 3. バックアップデータスキャン
    log "INFO" "Scanning backup data"
    clamscan -r /mnt/backup-hdd/mailserver/ \
        --infected \
        --log=/var/log/clamav/backup-scan.log \
        2>&1 | tee -a "${LOG_FILE}" || true

    # 4. rkhunter システムスキャン
    log "INFO" "Running rkhunter system scan"
    sudo rkhunter --check --skip-keypress --report-warnings-only \
        --log=/var/log/rkhunter/weekly-scan.log \
        2>&1 | tee -a "${LOG_FILE}" || true

    log "INFO" "=== Weekly Malware Scan Completed ==="
}

# メイン処理
main() {
    case "${SCAN_MODE}" in
        daily)
            daily_scan
            ;;
        weekly)
            weekly_scan
            ;;
    esac
}

main "$@"
EOF

chmod +x scan-mailserver.sh
```

### 5.6 scan-restored-data.sh 実装

```bash
cat > scan-restored-data.sh <<'EOF'
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/backup-config.sh"

# 引数解析
SOURCE_DIR=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --source)
            SOURCE_DIR="$2"
            shift 2
            ;;
        *)
            echo "Usage: $0 --source /path/to/restored/data"
            exit 1
            ;;
    esac
done

if [ -z "${SOURCE_DIR}" ]; then
    log "ERROR" "Source directory not specified"
    exit 1
fi

if [ ! -d "${SOURCE_DIR}" ]; then
    log "ERROR" "Source directory does not exist: ${SOURCE_DIR}"
    exit 1
fi

# メイン処理
main() {
    log "INFO" "=== Restored Data Scan Started ==="
    log "INFO" "Source: ${SOURCE_DIR}"

    # 1. ダウンロードファイルのスキャン
    log "INFO" "Scanning restored files with ClamAV"
    clamscan -r "${SOURCE_DIR}" \
        --infected \
        --remove \
        --log=/var/log/clamav/restore-scan.log \
        2>&1 | tee -a "${LOG_FILE}"

    local clamav_exit=$?

    # 2. rkhunterシステムスキャン（オプション）
    log "INFO" "Running rkhunter system scan"
    sudo rkhunter --check --skip-keypress --report-warnings-only \
        2>&1 | tee -a "${LOG_FILE}" || true

    # 結果判定
    if [ ${clamav_exit} -eq 0 ]; then
        log "INFO" "No malware detected"
        log "INFO" "=== Restored Data Scan Completed ==="
        return 0
    else
        log "ERROR" "Malware detected or scan error (exit code: ${clamav_exit})"
        log "INFO" "=== Restored Data Scan Completed with Errors ==="
        return 1
    fi
}

main "$@"
EOF

chmod +x scan-restored-data.sh
```

### 5.7 スクリプトテスト

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts

# 共通設定テスト
source ./backup-config.sh
echo "S3 Bucket: ${S3_BUCKET}"

# backup-to-s3.sh テスト（ドライラン）
# 注: Phase 10のバックアップが存在する必要があります
./backup-to-s3.sh

# scan-mailserver.sh テスト
./scan-mailserver.sh --daily
```

---

## 6. cron設定

### 6.1 cron スケジュール

```bash
# crontab編集
crontab -e
```

以下を追加:

```cron
# Phase 11-B: S3 Backup System

# 日次ローカルバックアップ（Phase 10）
0 3 * * * /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-mailserver.sh --daily >> /var/log/mailserver-backup/cron.log 2>&1

# S3レプリケーション
0 4 * * * /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-to-s3.sh >> /var/log/mailserver-backup/cron.log 2>&1

# 日次マルウェアスキャン
0 5 * * * /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/scan-mailserver.sh --daily >> /var/log/mailserver-backup/cron.log 2>&1

# 週次マルウェアスキャン（日曜）
0 6 * * 0 /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/scan-mailserver.sh --weekly >> /var/log/mailserver-backup/cron.log 2>&1
```

**重要な注意事項**:

cronは非対話シェルで実行されるため、以下の点に注意してください:

1. **環境変数は読み込まれない**: `~/.bashrc` は読み込まれません
2. **設定ファイルで対応済み**: `/etc/mailserver-backup/config` から `ADMIN_EMAIL` を読み込みます（セクション 2.5.2 で設定済み）
3. **AWS認証情報**: `~/.aws/credentials` と `~/.aws/config` はホームディレクトリから自動的に読み込まれます

### 6.2 cron動作確認

```bash
# 1. cron設定確認
crontab -l

# 2. 設定ファイル確認（すべての設定が正しいか）
cat /etc/mailserver-backup/config

# 3. スクリプトが設定を読み込めるか確認
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts
bash -c "source ./backup-config.sh && echo \"ADMIN_EMAIL: \${ADMIN_EMAIL}\" && echo \"AWS_PROFILE: \${AWS_PROFILE}\" && echo \"AWS_DEFAULT_REGION: \${AWS_DEFAULT_REGION}\""
# → すべての設定値が表示されればOK

# 4. AWS認証確認（cron環境をシミュレート）
bash -c "source ./backup-config.sh && aws sts get-caller-identity"
# → ユーザーIDとアカウントIDが表示されればOK

# 5. cronログ確認
tail -f /var/log/mailserver-backup/cron.log
```

---

## 7. 動作確認

### 7.1 手動バックアップ＆アップロード

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts

# 1. ローカルバックアップ実行
./backup-mailserver.sh --daily

# 2. S3アップロード実行
./backup-to-s3.sh

# 3. S3確認
aws s3 ls s3://$(terraform -chdir=../terraform/s3-backup output -raw s3_bucket_name)/daily/ \
  --profile mailserver-backup-admin
```

### 7.2 マルウェアスキャン確認

```bash
# 日次スキャン実行
./scan-mailserver.sh --daily

# ログ確認
tail -50 /var/log/clamav/daily-scan.log
tail -50 /var/log/clamav/host-daily-scan.log
```

### 7.3 リストアテスト

```bash
# 最新バックアップからリストア（テスト環境推奨）
./restore-from-s3.sh --component config

# ログ確認
tail -100 /var/log/mailserver-backup/s3-backup.log
```

### 7.4 CloudWatch Alarms テスト

```bash
# コスト監視アラーム確認
# 注: CloudWatch/SNS 操作には管理者プロファイルが必要
aws cloudwatch describe-alarms \
  --alarm-names mailserver-s3-backup-cost-warning mailserver-s3-backup-cost-critical \
  --region us-east-1 \
  --profile mailserver-backup

# SNS Subscription確認
aws sns list-subscriptions-by-topic \
  --topic-arn $(terraform -chdir=../terraform/s3-backup output -raw sns_topic_arn) \
  --region us-east-1 \
  --profile mailserver-backup
```

**テストアラート送信**（オプション）:

```bash
# テストメッセージ送信
aws sns publish \
  --topic-arn $(terraform -chdir=../terraform/s3-backup output -raw sns_topic_arn) \
  --subject "Test: S3 Backup Alert" \
  --message "This is a test alert from S3 backup system" \
  --region us-east-1 \
  --profile mailserver-backup
```

管理者メールアドレスにテストメールが届けばOK。

---

## 8. トラブルシューティング

### 8.1 よくあるエラー

#### 8.1.1 Terraform apply失敗: "Billing metrics not available"

**エラー**:
```
Error: Error creating CloudWatch Metric Alarm: UnsupportedOperation:
AWS/Billing metrics are only available in us-east-1
```

**原因**: CloudWatch Billing メトリクスは us-east-1 でのみ利用可能

**解決策**: cloudwatch.tf で `provider = aws.us_east_1` が指定されているか確認

```bash
grep "provider = aws.us_east_1" ../terraform/s3-backup/cloudwatch.tf
```

#### 8.1.2 S3アップロード失敗: "Access Denied"

**エラー**:
```
upload failed: ... to s3://... An error occurred (AccessDenied)
```

**原因**: IAMロールの権限不足、またはプロファイル設定ミス

**解決策**:

```bash
# 1. プロファイル確認
aws sts get-caller-identity --profile mailserver-backup-uploader

# 2. AssumeRole確認
aws sts assume-role \
  --role-arn $(terraform -chdir=../terraform/s3-backup output -raw backup_uploader_role_arn) \
  --role-session-name test \
  --profile mailserver-backup-dell

# 3. ~/.aws/config 確認
cat ~/.aws/config | grep -A 3 mailserver-backup-uploader
```

#### 8.1.3 SNS確認メールが届かない

**原因**: メールアドレス誤入力、またはスパムフォルダ

**解決策**:

```bash
# 1. SNS Subscription確認
# 注: SNS 操作には管理者プロファイルが必要
aws sns list-subscriptions-by-topic \
  --topic-arn $(terraform -chdir=../terraform/s3-backup output -raw sns_topic_arn) \
  --region us-east-1 \
  --profile mailserver-backup

# 2. PendingConfirmation の場合は再送信
aws sns subscribe \
  --topic-arn $(terraform -chdir=../terraform/s3-backup output -raw sns_topic_arn) \
  --protocol email \
  --notification-endpoint your-email@example.com \
  --region us-east-1 \
  --profile mailserver-backup
```

#### 8.1.4 ClamAV スキャン失敗: "Database outdated"

**エラー**:
```
LibClamAV Warning: ***********************************************************
LibClamAV Warning: ***  The virus database is older than 7 days!          ***
```

**解決策**:

```bash
# ウイルス定義更新
sudo freshclam

# clamd再起動
sudo systemctl restart clamd@scan
```

#### 8.1.5 rkhunter 警告多数

**原因**: 既知の誤検出（false positive）

**解決策**:

```bash
# 警告詳細確認
sudo grep Warning /var/log/rkhunter.log

# 既知の警告を無視する設定
sudo vim /etc/rkhunter.conf
# → ALLOWHIDDENDIR, ALLOWHIDDENFILE を追加

# プロパティ再初期化
sudo rkhunter --propupd
```

#### 8.1.6 cron実行時の環境変数エラー

**症状**:
```
ERROR: AWS authentication failed
ERROR: ADMIN_EMAIL not set, alert not sent
```

**原因**: cron が `/etc/mailserver-backup/config` を読み込めていない、または設定値が誤っている

**解決策**:

```bash
# 1. 設定ファイル存在確認
ls -la /etc/mailserver-backup/config

# 2. 設定ファイル内容確認
cat /etc/mailserver-backup/config

# 3. パーミッション確認（system-admin ユーザーが読み取り可能か）
ls -l /etc/mailserver-backup/config
# → -rw------- 1 system-admin system-admin であることを確認

# 4. 設定値確認（手動実行テスト）
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts
bash -c "source ./backup-config.sh && printenv | grep -E '(ADMIN_EMAIL|AWS_PROFILE|AWS_DEFAULT_REGION)'"

# 5. 設定ファイルが不正な場合は再作成
sudo tee /etc/mailserver-backup/config <<EOF
ADMIN_EMAIL="your-email@example.com"
AWS_PROFILE=mailserver-backup-uploader
AWS_DEFAULT_REGION=ap-northeast-1
EOF
sudo chmod 600 /etc/mailserver-backup/config
sudo chown system-admin:system-admin /etc/mailserver-backup/config
```

### 8.2 ログ確認

```bash
# S3バックアップログ
tail -100 /var/log/mailserver-backup/s3-backup.log

# ClamAVログ
tail -50 /var/log/clamav/daily-scan.log
tail -50 /var/log/clamav/host-daily-scan.log

# rkhunterログ
sudo tail -50 /var/log/rkhunter.log

# cronログ
tail -100 /var/log/mailserver-backup/cron.log
```

### 8.3 緊急時の対応

#### シナリオ1: S3アップロードが連続失敗

```bash
# 1. 手動アップロード試行
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts
./backup-to-s3.sh

# 2. ネットワーク確認
ping -c 3 s3.ap-northeast-1.amazonaws.com

# 3. AWS認証確認
aws sts get-caller-identity --profile mailserver-backup-uploader

# 4. S3バケット確認
aws s3 ls s3://$(terraform -chdir=../terraform/s3-backup output -raw s3_bucket_name)/ \
  --profile mailserver-backup-uploader
```

#### シナリオ2: マルウェア検出

```bash
# 1. 隔離ファイル確認
ls -lh /var/quarantine/

# 2. 詳細ログ確認
tail -100 /var/log/clamav/daily-scan.log | grep FOUND

# 3. 感染ファイル特定
clamscan --infected /path/to/suspicious/file

# 4. 前日バックアップからリストア
./restore-from-s3.sh --date $(date -d "yesterday" '+%Y-%m-%d') --component all
```

#### シナリオ3: Object Lock期間内の誤削除対応

```bash
# Object Lockにより削除不可（正常動作）
# 復旧: バージョニングから復元

# 1. バージョン一覧取得
aws s3api list-object-versions \
  --bucket $(terraform -chdir=../terraform/s3-backup output -raw s3_bucket_name) \
  --prefix daily/2025-11-07/ \
  --profile mailserver-backup-admin

# 2. 最新バージョンを復元（DeleteMarker削除）
# → Object Lockにより保護されているため、自動復元される
```

---

## 9. 完了チェックリスト

### 9.1 Terraform

- [ ] S3バケット作成完了
- [ ] Object Lock (COMPLIANCE, 30日) 有効
- [ ] IAMロール・ポリシー作成完了
- [ ] CloudWatch Alarms 作成完了（us-east-1）
- [ ] SNS Topic作成完了（us-east-1）
- [ ] SNS確認メール対応完了

### 9.2 マルウェアスキャン

- [ ] Host ClamAVインストール完了
- [ ] rkhunterインストール完了
- [ ] ウイルス定義更新完了
- [ ] 隔離ディレクトリ作成完了
- [ ] テストスキャン成功

### 9.3 スクリプト

- [ ] backup-config.sh 作成完了
- [ ] backup-to-s3.sh 実装・テスト完了
- [ ] restore-from-s3.sh 実装・テスト完了
- [ ] scan-mailserver.sh 実装・テスト完了
- [ ] scan-restored-data.sh 実装・テスト完了

### 9.4 cron

- [ ] cron設定完了
- [ ] cron動作確認完了

### 9.5 動作確認

- [ ] 手動バックアップ→S3アップロード成功
- [ ] マルウェアスキャン成功
- [ ] リストアテスト成功
- [ ] CloudWatch Alarms動作確認完了
- [ ] SNSメール通知確認完了

---

## 10. 次のステップ

Phase 11-B実装が完了したら、以下を検討してください:

1. **監視強化**: CloudWatch DashboardでS3コスト・アップロード成功率を可視化
2. **自動テスト**: 月次で自動リストアテストを実施
3. **ドキュメント更新**: 運用手順書・障害対応手順書の作成
4. **Phase 11-C検討**: AWS移行計画の策定

---

## 付録

### A. 参考ドキュメント

- [05_s3backup_requirements.md](05_s3backup_requirements.md) - 要件定義
- [06_s3backup_design.md](06_s3backup_design.md) - 設計書
- [03_implementation.md](03_implementation.md) - Phase 10実装ガイド

### B. 用語集

| 用語 | 説明 |
|------|------|
| **Object Lock** | S3のWORM（Write Once Read Many）機能 |
| **COMPLIANCE Mode** | 削除不可期間中、root含め誰も削除できないモード |
| **GLACIER** | S3の低コストアーカイブストレージクラス |
| **IAM Role** | AWSリソースへのアクセス権限を定義する仕組み |
| **AssumeRole** | 一時的に別のIAMロールの権限を取得する操作 |
| **ClamAV** | オープンソースのウイルススキャンエンジン |
| **rkhunter** | Linuxのルートキット検出ツール |

### C. 変更履歴

| バージョン | 日付 | 変更内容 | 作成者 |
|----------|------|---------|--------|
| 1.0 | 2025-11-07 | 初版作成（Phase 11-B実装ガイド） | system-admin |
| 1.1 | 2025-11-07 | Object Lock有効化修正、CloudWatch/SNS確認コマンドのプロファイル修正、cron環境変数対応（/etc/mailserver-backup/config追加） | system-admin |
| 1.2 | 2025-11-07 | AWS環境変数を/etc/mailserver-backup/configに統合、restore-from-s3.shのプロファイル継承修正、cron動作確認手順強化 | system-admin |

---

**END OF DOCUMENT**
