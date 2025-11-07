# S3バックアップシステム設計書（Phase 11-B）

**作成日**: 2025-11-07
**バージョン**: 1.0
**対象システム**: Dell Mailserver → AWS S3 Replication
**前提ドキュメント**: [05_s3backup_requirements.md](./05_s3backup_requirements.md)

---

## 📋 目次

1. [システムアーキテクチャ](#1-システムアーキテクチャ)
2. [S3バケット設計](#2-s3バケット設計)
3. [IAM設計](#3-iam設計)
4. [スクリプト設計](#4-スクリプト設計)
5. [マルウェアスキャン設計](#5-マルウェアスキャン設計)
6. [Terraform設計](#6-terraform設計)
7. [エラーハンドリング設計](#7-エラーハンドリング設計)
8. [テスト設計](#8-テスト設計)

---

## 1. システムアーキテクチャ

### 1.1 全体構成

```
┌─────────────────────────────────────────────────────────────────┐
│ Dell Mailserver (Rocky Linux 9.6)                              │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Phase 10: ローカルバックアップ                            │  │
│  │  cron: 03:00 daily                                        │  │
│  │  ↓                                                        │  │
│  │  /mnt/backup-hdd/mailserver/daily/YYYY-MM-DD/            │  │
│  │    ├── mail/ (rsync増分)                                 │  │
│  │    ├── mysql/ (mysqldump gzip)                           │  │
│  │    ├── config/ (tar.gz)                                  │  │
│  │    ├── dkim/ (tar.gz)                                    │  │
│  │    ├── ssl/ (tar.gz)                                     │  │
│  │    └── checksums.sha256                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                      │
│                          ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Phase 11-B: S3レプリケーション                            │  │
│  │  cron: 04:00 daily                                        │  │
│  │  Script: backup-to-s3.sh                                  │  │
│  │  ↓                                                        │  │
│  │  AWS CLI (aws s3 sync)                                   │  │
│  │    - IAM Role: mailserver-backup-uploader                │  │
│  │    - TLS 1.2 暗号化                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                      │
│                          ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Phase 11-B: マルウェアスキャン                            │  │
│  │  cron: 05:00 daily / 06:00 weekly                        │  │
│  │  Script: scan-mailserver.sh                               │  │
│  │  ↓                                                        │  │
│  │  ClamAV + rkhunter                                       │  │
│  │    - Docker ClamAV (メール)                              │  │
│  │    - Host ClamAV (バックアップ)                          │  │
│  │    - rkhunter (システム)                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                          │
                          │ Internet (TLS 1.2+)
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ AWS S3 (ap-northeast-1)                                         │
│                                                                 │
│  s3://mailserver-backup-ACCOUNT-ID/                            │
│    ├── daily/                                                  │
│    │   ├── 2025-11-07/                                        │
│    │   ├── 2025-11-08/                                        │
│    │   └── ...                                                │
│    └── latest -> daily/2025-11-08/                            │
│                                                                 │
│  Features:                                                      │
│    - Object Lock: COMPLIANCE (30日)                           │
│    - Versioning: Enabled                                       │
│    - Encryption: AES-256 (SSE-S3)                             │
│    - Lifecycle:                                                │
│      - STANDARD: 30日                                         │
│      - GLACIER: 31-90日                                       │
│      - DELETE: 90日後                                         │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 データフロー

**通常運用時**:
```
03:00 backup-mailserver.sh --daily
  ↓ ローカルバックアップ作成
04:00 backup-to-s3.sh
  ↓ S3アップロード
05:00 scan-mailserver.sh --daily
  ↓ 日次スキャン
06:00 scan-mailserver.sh --weekly (日曜のみ)
  ↓ 週次スキャン
```

**災害復旧時**:
```
1. Git clone (IaC取得)
2. terraform apply (EC2再構築)
3. docker compose up -d (Dell環境セットアップ)
4. restore-from-s3.sh --date latest --component all
   ↓ S3ダウンロード
   ↓ チェックサム検証
   ↓ マルウェアスキャン
   ↓ restore-mailserver.sh 呼び出し
5. scan-restored-data.sh (リストア後検証)
6. test-mailserver.sh (動作確認)
```

---

## 2. S3バケット設計

### 2.1 バケット命名規則

```
s3://mailserver-backup-{AWS_ACCOUNT_ID}/
```

**理由**:
- グローバルユニーク性の保証（ACCOUNT-ID含む）
- 用途明確化（mailserver-backup）
- セキュリティ（アカウントID隠蔽は意味なし、管理容易性優先）

### 2.2 ディレクトリ構造

```
s3://mailserver-backup-123456789012/
├── daily/
│   ├── 2025-11-01/
│   │   ├── mail/
│   │   │   └── vmail/
│   │   ├── mysql/
│   │   │   ├── usermgmt.sql.gz
│   │   │   └── roundcubemail.sql.gz
│   │   ├── config/
│   │   │   ├── config.tar.gz
│   │   │   └── .env
│   │   ├── dkim/
│   │   │   └── opendkim-keys.tar.gz
│   │   ├── ssl/
│   │   │   └── certbot.tar.gz
│   │   ├── checksums.sha256
│   │   └── backup.log
│   ├── 2025-11-02/
│   └── ...
```

**注**: IaC（docker-compose.yml, Terraform等）はGitHub管理対象のため、S3バックアップには含めない（要件書 05_s3backup_requirements.md:41-44, 159）

**latest の実装と更新管理**:

S3はシンボリックリンク非対応のため、prefix検索で最新を取得（タグ管理は不要）:

```bash
# 最新バックアップ日付取得（backup-to-s3.sh / restore-from-s3.sh で使用）
get_latest_backup_date() {
    aws s3 ls "s3://${S3_BUCKET}/daily/" --profile mailserver-backup \
        | awk '{print $2}' \
        | sed 's#/##g' \
        | sort -r \
        | head -n 1
}
```

**更新管理**: `backup-to-s3.sh` が毎日自動実行されることで、常に最新のバックアップがS3に追加される。手動での latest タグ更新は不要（prefix検索で自動的に最新を取得）。

### 2.3 S3バケットポリシー

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::mailserver-backup-ACCOUNT-ID",
        "arn:aws:s3:::mailserver-backup-ACCOUNT-ID/*"
      ],
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    },
    {
      "Sid": "DenyUnencryptedObjectUploads",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::mailserver-backup-ACCOUNT-ID/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "AES256"
        }
      }
    },
    {
      "Sid": "DenyObjectLockBypass",
      "Effect": "Deny",
      "Principal": "*",
      "Action": [
        "s3:BypassGovernanceRetention",
        "s3:PutObjectRetention",
        "s3:PutObjectLegalHold"
      ],
      "Resource": "arn:aws:s3:::mailserver-backup-ACCOUNT-ID/*",
      "Condition": {
        "StringNotEquals": {
          "aws:PrincipalArn": "arn:aws:iam::ACCOUNT-ID:role/mailserver-backup-uploader"
        }
      }
    }
  ]
}
```

### 2.4 Object Lock設定

```json
{
  "ObjectLockEnabled": "Enabled",
  "ObjectLockConfiguration": {
    "ObjectLockEnabled": "Enabled",
    "Rule": {
      "DefaultRetention": {
        "Mode": "COMPLIANCE",
        "Days": 30
      }
    }
  }
}
```

**COMPLIANCE mode の特徴**:
- rootユーザーでも削除不可能
- 保持期間変更不可能
- 改ざん完全防止

### 2.5 バージョニング設定

```json
{
  "Status": "Enabled"
}
```

**理由**:
- Object Lock の前提条件
- 誤削除時のリカバリー
- 上書き攻撃への対策

### 2.6 ライフサイクルポリシー

```json
{
  "Rules": [
    {
      "Id": "TransitionToGlacier",
      "Status": "Enabled",
      "Prefix": "daily/",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 90
      }
    }
  ]
}
```

**ストレージクラス遷移**:
- 0-30日: STANDARD（即座アクセス）
- 31-90日: GLACIER（数時間取得）
- 90日後: 削除

---

## 3. IAM設計

### 3.1 IAM Role: mailserver-backup-uploader

**用途**: Dell環境からS3へのアップロード専用

**Trust Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT-ID:user/dell-system-admin"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Permissions Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowS3Upload",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:PutObjectRetention",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::mailserver-backup-ACCOUNT-ID",
        "arn:aws:s3:::mailserver-backup-ACCOUNT-ID/daily/*"
      ]
    },
    {
      "Sid": "DenyDeleteObject",
      "Effect": "Deny",
      "Action": [
        "s3:DeleteObject",
        "s3:DeleteObjectVersion"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3.2 IAM Role: mailserver-backup-admin

**用途**: 管理者用（バックアップ確認、リストア）

**Trust Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT-ID:user/admin-user"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Permissions Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowReadOnly",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:ListBucket",
        "s3:ListBucketVersions"
      ],
      "Resource": [
        "arn:aws:s3:::mailserver-backup-ACCOUNT-ID",
        "arn:aws:s3:::mailserver-backup-ACCOUNT-ID/*"
      ]
    },
    {
      "Sid": "DenyDelete",
      "Effect": "Deny",
      "Action": [
        "s3:DeleteObject",
        "s3:DeleteObjectVersion"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3.3 IAM User: dell-system-admin

**用途**: Dell環境での AWS CLI 実行用

**Access Key**:
- Access Key ID: AKIA... (生成時に保存)
- Secret Access Key: (KeePass等で管理)
- ローテーション: 90日ごと

**Attached Policies**:
- `sts:AssumeRole` → `mailserver-backup-uploader`

**AWS CLI設定**:
```bash
# ~/.aws/config
[profile mailserver-backup]
role_arn = arn:aws:iam::ACCOUNT-ID:role/mailserver-backup-uploader
source_profile = dell-system-admin

# ~/.aws/credentials
[dell-system-admin]
aws_access_key_id = AKIA...
aws_secret_access_key = ...
```

---

## 4. スクリプト設計

### 4.1 backup-to-s3.sh

**目的**: ローカル日次バックアップをS3にアップロード

**処理フロー**:
```
1. 初期化
   - 環境変数読み込み (backup-config.sh)
   - ロックファイル確認（多重実行防止）
   - AWS CLI認証確認

2. バックアップ対象確認
   - 前日のバックアップディレクトリ存在確認
   - checksums.sha256 整合性検証

3. S3アップロード
   - aws s3 sync --sse AES256
   - アップロード進捗ログ記録
   - ETag検証

4. アップロード後検証
   - S3オブジェクト一覧取得
   - サイズ比較
   - チェックサム再検証（オプション）

5. クリーンアップ
   - ロックファイル削除
   - 統計情報ログ記録
   - 通知送信（失敗時）
```

**擬似コード**:
```bash
#!/bin/bash
set -euo pipefail

source "${SCRIPT_DIR}/backup-config.sh"

# 初期化
initialize() {
    check_lock_file
    check_aws_cli
    check_iam_credentials
}

# バックアップ検証
validate_local_backup() {
    local backup_date=$(date -d "yesterday" '+%Y-%m-%d')
    local backup_dir="${DAILY_BACKUP_DIR}/${backup_date}"

    if [ ! -d "${backup_dir}" ]; then
        log "ERROR" "Backup directory not found: ${backup_dir}"
        return 1
    fi

    # チェックサム検証
    cd "${backup_dir}"
    sha256sum -c checksums.sha256 || return 1
}

# S3アップロード
upload_to_s3() {
    local backup_date=$(date -d "yesterday" '+%Y-%m-%d')
    local source_dir="${DAILY_BACKUP_DIR}/${backup_date}"
    local s3_dest="s3://${S3_BUCKET}/daily/${backup_date}/"

    log "INFO" "Uploading to S3: ${s3_dest}"

    aws s3 sync "${source_dir}/" "${s3_dest}" \
        --profile mailserver-backup \
        --sse AES256 \
        --storage-class STANDARD \
        --no-progress \
        2>&1 | tee -a "${LOG_FILE}"

    local exit_code=${PIPESTATUS[0]}

    if [ ${exit_code} -eq 0 ]; then
        log "INFO" "Upload successful"
        return 0
    else
        log "ERROR" "Upload failed with exit code: ${exit_code}"
        return 1
    fi
}

# アップロード検証
verify_s3_upload() {
    local backup_date=$(date -d "yesterday" '+%Y-%m-%d')
    local s3_path="s3://${S3_BUCKET}/daily/${backup_date}/"

    # オブジェクト数確認
    local s3_count=$(aws s3 ls "${s3_path}" --recursive --profile mailserver-backup | wc -l)
    local local_count=$(find "${DAILY_BACKUP_DIR}/${backup_date}" -type f | wc -l)

    if [ ${s3_count} -ne ${local_count} ]; then
        log "ERROR" "File count mismatch: S3=${s3_count}, Local=${local_count}"
        return 1
    fi

    log "INFO" "Verification successful: ${s3_count} files"
    return 0
}

# メイン処理
main() {
    initialize || exit 1
    validate_local_backup || exit 1
    upload_to_s3 || exit 1
    verify_s3_upload || exit 1

    log "INFO" "S3 backup completed successfully"
}

main "$@"
```

### 4.2 restore-from-s3.sh

**目的**: S3からダウンロード → マルウェアスキャン → restore-mailserver.sh 呼び出し

**処理フロー**:
```
1. 引数解析
   --date: バックアップ日付（YYYY-MM-DD or "latest"）
   --component: リストア対象（all, mail, mysql, config, etc.）

2. S3ダウンロード
   - aws s3 sync
   - ダウンロード先: /tmp/s3-restore-$$/${date}/

3. チェックサム検証
   - sha256sum -c checksums.sha256

4. マルウェアスキャン
   - scan-restored-data.sh --source /tmp/s3-restore-$$/
   - 検出時: 前日バックアップにフォールバック

5. データリストア
   - restore-mailserver.sh --from /tmp/s3-restore-$$ --component ${component}

6. クリーンアップ
   - /tmp/s3-restore-$$/ 削除
```

**擬似コード**:
```bash
#!/bin/bash
set -euo pipefail

source "${SCRIPT_DIR}/backup-config.sh"

# 引数解析
parse_args() {
    BACKUP_DATE="latest"
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
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
}

# 最新バックアップ日付取得
get_latest_backup_date() {
    aws s3 ls "s3://${S3_BUCKET}/daily/" --profile mailserver-backup \
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

    log "INFO" "Downloading from S3: s3://${S3_BUCKET}/daily/${date}/"

    aws s3 sync "s3://${S3_BUCKET}/daily/${date}/" "${restore_dir}/" \
        --profile mailserver-backup \
        --no-progress \
        2>&1 | tee -a "${LOG_FILE}"

    echo "${restore_dir}"
}

# マルウェアスキャン
scan_backup() {
    local restore_dir="$1"

    log "INFO" "Scanning backup for malware..."

    if "${SCRIPT_DIR}/scan-restored-data.sh" --source "${restore_dir}"; then
        log "INFO" "Scan completed: No malware detected"
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

    log "INFO" "Restoring ${component} from ${restore_dir}"

    "${SCRIPT_DIR}/restore-mailserver.sh" \
        --from "${restore_dir}" \
        --component "${component}"
}

# メイン処理
main() {
    parse_args "$@"

    # 最新日付取得
    if [ "${BACKUP_DATE}" = "latest" ]; then
        BACKUP_DATE=$(get_latest_backup_date)
    fi

    log "INFO" "Restoring from backup: ${BACKUP_DATE}"

    # S3ダウンロード
    local restore_dir=$(download_from_s3 "${BACKUP_DATE}")

    # マルウェアスキャン
    if ! scan_backup "${restore_dir}"; then
        log "WARNING" "Malware detected, trying previous day..."
        local previous_date=$(date -d "${BACKUP_DATE} -1 day" '+%Y-%m-%d')
        restore_dir=$(download_from_s3 "${previous_date}")
        scan_backup "${restore_dir}" || exit 1
    fi

    # リストア実行
    restore_data "${restore_dir}" "${COMPONENT}"

    # クリーンアップ
    rm -rf "/tmp/s3-restore-$$"

    log "INFO" "Restore completed successfully"
}

main "$@"
```

### 4.3 scan-mailserver.sh

**目的**: 定期マルウェアスキャン（日次/週次）

**処理フロー**:
```
1. 引数解析
   --daily: 日次スキャン
   --weekly: 週次スキャン

2. 日次スキャン
   - Docker ClamAV: メールデータ
   - Host ClamAV: メールデータディレクトリ

3. 週次スキャン（日次に加えて）
   - Host ClamAV: バックアップデータ
   - rkhunter: システム全体

4. 検出時処理
   - 自動隔離: /var/quarantine/
   - アラートメール送信
   - 詳細ログ記録

5. レポート生成
   - スキャン結果サマリー
   - 検出ファイル一覧
   - 推奨アクション
```

### 4.4 scan-restored-data.sh

**目的**: リストア後のマルウェアスキャン

**処理フロー**:
```
1. 引数解析
   --source: スキャン対象ディレクトリ

2. バックアップファイルスキャン
   - ClamAV: 全ファイル

3. システムスキャン
   - rkhunter: ルートキット検査

4. 検出時処理
   - 即座にスキャン中止
   - エラーコード返却（restore-from-s3.sh がフォールバック）

5. スキャンレポート
   - 検出有無
   - 検出ファイル詳細
```

---

## 5. マルウェアスキャン設計

### 5.1 ClamAV設定

**Docker ClamAVコンテナ**（既存）:
- 用途: メールデータのリアルタイムスキャン
- 設定: `/opt/onprem-infra-system/project-root-infra/services/mailserver/config/clamav/`

**Host ClamAV**（新規）:
```bash
# インストール
sudo dnf install -y clamav clamav-update clamd

# 定義ファイル更新
sudo freshclam

# 設定ファイル: /etc/clamd.d/scan.conf
LocalSocket /var/run/clamd.scan/clamd.sock
LogFile /var/log/clamav/clamd.log
LogTime yes
LogFileMaxSize 10M
LogRotate yes
```

**スキャンオプション**:
```bash
clamscan \
  --recursive \
  --infected \
  --move=/var/quarantine/ \
  --log=/var/log/clamav/scan.log \
  /path/to/scan/
```

### 5.2 rkhunter設定

**インストール**:
```bash
sudo dnf install -y rkhunter
```

**設定ファイル**: `/etc/rkhunter.conf`
```bash
MIRRORS_MODE=0
UPDATE_MIRRORS=1
WEB_CMD="/usr/bin/wget"
ENABLE_TESTS=all
DISABLE_TESTS=suspscan hidden_procs deleted_files packet_cap_apps apps

SCRIPTWHITELIST=/usr/bin/egrep
SCRIPTWHITELIST=/usr/bin/fgrep
SCRIPTWHITELIST=/usr/bin/which
SCRIPTWHITELIST=/usr/bin/ldd

ALLOWHIDDENDIR=/dev/.udev
ALLOWHIDDENDIR=/dev/.static
ALLOWHIDDENDIR=/dev/.initramfs

PORT_WHITELIST=TCP:22
PORT_WHITELIST=TCP:25
PORT_WHITELIST=TCP:80
PORT_WHITELIST=TCP:443
PORT_WHITELIST=TCP:587
PORT_WHITELIST=TCP:993
```

**実行コマンド**:
```bash
rkhunter \
  --check \
  --skip-keypress \
  --report-warnings-only \
  --log /var/log/rkhunter/scan.log
```

### 5.3 スキャンスケジュール

| 時刻 | スキャン種別 | 対象 | ツール |
|-----|------------|------|-------|
| 05:00 daily | 日次メール | /services/mailserver/data/mail/ | Docker ClamAV<br>Host ClamAV |
| 06:00 Sunday | 週次バックアップ | /mnt/backup-hdd/mailserver/ | Host ClamAV |
| 06:00 Sunday | 週次システム | / | rkhunter |

### 5.4 隔離ディレクトリ

```bash
# ディレクトリ作成
sudo mkdir -p /var/quarantine
sudo chown system-admin:system-admin /var/quarantine
sudo chmod 700 /var/quarantine

# ログローテーション
sudo tee /etc/logrotate.d/clamav-host > /dev/null <<EOF
/var/log/clamav/*.log {
    daily
    rotate 90
    compress
    delaycompress
    missingok
    notifempty
    create 0600 clamav clamav
}
EOF
```

---

## 6. Terraform設計

### 6.1 ディレクトリ構造

```
services/mailserver/terraform/s3-backup/
├── main.tf
├── variables.tf
├── outputs.tf
├── s3.tf
├── iam.tf
├── lifecycle.tf
└── README.md
```

### 6.2 main.tf

```hcl
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
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
```

### 6.2.5 variables.tf

```hcl
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
```

### 6.3 s3.tf

```hcl
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
      days = 30
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
      },
      {
        Sid    = "DenyUnencryptedObjectUploads"
        Effect = "Deny"
        Principal = "*"
        Action = "s3:PutObject"
        Resource = "${aws_s3_bucket.mailserver_backup.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "AES256"
          }
        }
      }
    ]
  })
}

data "aws_caller_identity" "current" {}
```

### 6.4 iam.tf

```hcl
# IAM User: dell-system-admin
resource "aws_iam_user" "dell_system_admin" {
  name = "dell-system-admin"
  path = "/mailserver/"

  tags = {
    Purpose = "S3 Backup Upload"
    Server  = "Dell Mailserver"
  }
}

# IAM Role: mailserver-backup-uploader
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
          "s3:PutObjectAcl",
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

# IAM Role: mailserver-backup-admin
resource "aws_iam_role" "backup_admin" {
  name = "mailserver-backup-admin"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "backup_admin" {
  name = "S3BackupReadOnly"
  role = aws_iam_role.backup_admin.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowReadOnly"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:ListBucket",
          "s3:ListBucketVersions"
        ]
        Resource = [
          aws_s3_bucket.mailserver_backup.arn,
          "${aws_s3_bucket.mailserver_backup.arn}/*"
        ]
      },
      {
        Sid    = "DenyDelete"
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
```

### 6.5 lifecycle.tf

```hcl
resource "aws_s3_bucket_lifecycle_configuration" "mailserver_backup" {
  bucket = aws_s3_bucket.mailserver_backup.id

  rule {
    id     = "daily-backups-lifecycle"
    status = "Enabled"

    filter {
      prefix = "daily/"
    }

    transition {
      days          = 30
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
```

### 6.6 CloudWatch Alarms（コスト監視）

**2段階コスト閾値アラート**:

```hcl
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
```

**閾値の根拠**:
- **10円/月**: 現行データ量4MB/日での想定コスト（要件書 05_s3backup_requirements.md:110）
- **100円/月**: 10倍の増加は異常（ランサムウェア活動や意図しないデータ増加の可能性）

**重要な技術的制約**:
- AWS/Billing メトリクスは **us-east-1 リージョンでのみ利用可能**（AWSの仕様）
- CloudWatch Alarms と SNS Topic を us-east-1 に配置（`provider = aws.us_east_1`）
- S3バケット自体は ap-northeast-1 に配置（データ主権・レイテンシ最適化）

---

## 7. エラーハンドリング設計

### 7.1 エラー分類

| エラー種別 | 重要度 | 対処方法 |
|-----------|--------|---------|
| **AWS認証失敗** | 🔴 HIGH | リトライ不可、アラート送信 |
| **S3アップロード失敗** | 🔴 HIGH | 3回リトライ（指数バックオフ） |
| **チェックサム不一致** | 🔴 HIGH | アップロード中止、前回バックアップ使用 |
| **マルウェア検出** | 🔴 HIGH | 隔離、アラート送信、前日バックアップ使用 |
| **ディスク容量不足** | 🟡 MEDIUM | アラート送信、古いバックアップ削除 |
| **ネットワークタイムアウト** | 🟢 LOW | リトライ（最大3回） |

### 7.2 リトライロジック

```bash
retry_with_backoff() {
    local max_attempts=3
    local timeout=1
    local attempt=0
    local exitCode=0

    while (( attempt < max_attempts )); do
        if "$@"; then
            return 0
        else
            exitCode=$?
        fi

        log "WARNING" "Command failed (attempt $((attempt + 1))/${max_attempts}): $*"

        if (( attempt < max_attempts - 1 )); then
            log "INFO" "Retrying in ${timeout}s..."
            sleep $timeout
            timeout=$((timeout * 2))  # Exponential backoff
        fi

        attempt=$((attempt + 1))
    done

    log "ERROR" "Command failed after ${max_attempts} attempts: $*"
    return $exitCode
}
```

### 7.3 アラート設計

**通知トリガー**:
- S3アップロード失敗（3回リトライ後）
- マルウェア検出
- ディスク容量80%超過
- **コスト閾値超過（2段階）**:
  - **WARNING**: 月次コスト10円超過（現行データ量の想定値超過）
  - **CRITICAL**: 月次コスト100円超過（異常な増加、調査必要）

**通知方法**:
```bash
send_alert() {
    local severity="$1"  # CRITICAL, ERROR, WARNING
    local message="$2"

    local subject="[${severity}] Mailserver S3 Backup Alert"

    echo "${message}" | mail -s "${subject}" "${ADMIN_EMAIL}"

    # CloudWatch Logs (オプション)
    aws logs put-log-events \
        --log-group-name /mailserver/s3-backup \
        --log-stream-name alerts \
        --log-events timestamp=$(date +%s000),message="${message}"
}
```

---

## 8. テスト設計

### 8.1 単体テスト

**backup-to-s3.sh**:
```bash
# Test 1: AWS CLI認証確認
test_aws_authentication() {
    aws sts get-caller-identity --profile mailserver-backup
    assert_exit_code 0
}

# Test 2: S3アップロード
test_s3_upload() {
    create_test_backup_dir
    run_backup_to_s3
    assert_exit_code 0
    verify_s3_objects
}

# Test 3: チェックサム検証
test_checksum_verification() {
    create_test_backup_with_invalid_checksum
    run_backup_to_s3
    assert_exit_code 1  # Should fail
}
```

**restore-from-s3.sh**:
```bash
# Test 4: S3ダウンロード
test_s3_download() {
    run_restore_from_s3 --date 2025-11-07 --component mail
    assert_exit_code 0
    assert_directory_exists /tmp/s3-restore-$$/2025-11-07/mail/
}

# Test 5: マルウェア検出時のフォールバック
test_malware_fallback() {
    inject_test_malware_to_s3 2025-11-07
    run_restore_from_s3 --date 2025-11-07 --component mail
    assert_uses_previous_day_backup
}
```

**scan-mailserver.sh**:
```bash
# Test 6: ClamAV定期スキャン
test_daily_scan() {
    run_scan_mailserver --daily
    assert_exit_code 0
    assert_log_contains "Scan completed"
}

# Test 7: マルウェア検出
test_malware_detection() {
    create_eicar_test_file /tmp/test-malware
    run_clamscan /tmp/test-malware
    assert_exit_code 1  # Malware detected
    assert_file_quarantined /tmp/test-malware
}
```

### 8.2 統合テスト

**End-to-End テスト**:
```bash
# Test 8: 完全バックアップ＆リストア
test_full_backup_restore_cycle() {
    # 1. ローカルバックアップ作成
    run_backup_mailserver --daily

    # 2. S3アップロード
    run_backup_to_s3

    # 3. S3からリストア
    run_restore_from_s3 --date latest --component all

    # 4. データ整合性確認
    compare_mail_data_checksums
    compare_mysql_data
}

# Test 9: ランサムウェアシミュレーション
test_ransomware_recovery() {
    # 1. 初期データ作成
    create_test_mail_data

    # 2. バックアップ作成
    run_backup_mailserver --daily
    run_backup_to_s3

    # 3. データ破壊（ランサムウェア模擬）
    encrypt_all_mail_data

    # 4. S3からリストア
    run_restore_from_s3 --date latest --component all

    # 5. データ復旧確認
    assert_mail_data_restored
}
```

### 8.3 性能テスト

**アップロード時間測定**:
```bash
# Test 10: 4MB バックアップのアップロード時間
test_upload_performance_4mb() {
    create_test_backup 4MB

    local start_time=$(date +%s)
    run_backup_to_s3
    local end_time=$(date +%s)

    local duration=$((end_time - start_time))

    # 要件: 5分以内
    assert_less_than $duration 300
}

# Test 11: 100MB バックアップのアップロード時間
test_upload_performance_100mb() {
    create_test_backup 100MB

    local start_time=$(date +%s)
    run_backup_to_s3
    local end_time=$(date +%s)

    local duration=$((end_time - start_time))

    # 要件: 30分以内
    assert_less_than $duration 1800
}
```

### 8.4 セキュリティテスト

**Object Lock検証**:
```bash
# Test 12: COMPLIANCE mode削除不可確認
test_object_lock_prevents_deletion() {
    upload_test_object_to_s3

    # rootユーザーでも削除できないことを確認
    aws s3 rm s3://mailserver-backup-ACCOUNT-ID/daily/2025-11-07/test.txt \
        --profile root-user

    assert_exit_code 1  # Access Denied
}

# Test 13: TLS強制確認
test_enforce_tls() {
    # HTTP経由のアップロード試行
    curl -X PUT http://s3.ap-northeast-1.amazonaws.com/mailserver-backup-ACCOUNT-ID/test.txt

    assert_response_code 403  # Forbidden
}
```

---

## 📝 付録

### A. 関連ドキュメント

- [05_s3backup_requirements.md](./05_s3backup_requirements.md) - 要件定義書
- [07_s3backup_implementation.md](./07_s3backup_implementation.md) - 実装ガイド（次作成）
- [Mailserver README](../README.md) - Mailserver全体ドキュメント

### B. コマンドリファレンス

**AWS CLI**:
```bash
# S3アップロード
aws s3 sync /local/path/ s3://bucket/prefix/ --profile mailserver-backup

# S3ダウンロード
aws s3 sync s3://bucket/prefix/ /local/path/ --profile mailserver-backup

# オブジェクト一覧
aws s3 ls s3://bucket/prefix/ --recursive --profile mailserver-backup

# IAM Role確認
aws sts get-caller-identity --profile mailserver-backup
```

**Terraform**:
```bash
# 初期化
terraform init

# プラン確認
terraform plan

# 適用
terraform apply

# 破棄
terraform destroy
```

**ClamAV**:
```bash
# 定義ファイル更新
sudo freshclam

# スキャン実行
clamscan -r /path/to/scan/ --infected --log=/var/log/clamav/scan.log

# デーモン起動
sudo systemctl start clamd@scan
```

**rkhunter**:
```bash
# データベース更新
sudo rkhunter --update

# スキャン実行
sudo rkhunter --check --skip-keypress --report-warnings-only
```

### C. 変更履歴

| バージョン | 日付 | 変更内容 | 作成者 |
|----------|------|---------|--------|
| 1.0 | 2025-11-07 | 初版作成（Phase 11-B設計書） | system-admin |
| 1.1 | 2025-11-07 | レビュー修正（コスト閾値2段階化、IaC除外、latest更新管理明確化） | system-admin |
| 1.2 | 2025-11-07 | us-east-1プロバイダ追加（Billing メトリクス対応） | system-admin |
| 1.3 | 2025-11-07 | Object Lock有効化修正（object_lock_enabled = true追加） | system-admin |

---

**END OF DOCUMENT**
