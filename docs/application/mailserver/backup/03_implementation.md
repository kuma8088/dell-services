# メールサーバーバックアップシステム実装ガイド

**作成日**: 2025-11-07
**バージョン**: 1.0
**対象システム**: Dell Mailserver (Docker Compose 環境)
**前提ドキュメント**: [01_requirements.md](./01_requirements.md), [02_design.md](./02_design.md)

---

## 📋 目次

1. [実装前の準備](#1-実装前の準備)
2. [必要なパッケージのインストール](#2-必要なパッケージのインストール)
3. [ディレクトリ構造の作成](#3-ディレクトリ構造の作成)
4. [設定ファイルの作成](#4-設定ファイルの作成)
5. [バックアップスクリプトの実装](#5-バックアップスクリプトの実装)
6. [cron設定](#6-cron設定)
7. [初回実行とテスト](#7-初回実行とテスト)
8. [リストアスクリプトの実装](#8-リストアスクリプトの実装)
9. [トラブルシューティング](#9-トラブルシューティング)

---

## 1. 実装前の準備

### 1.1 前提条件確認

```bash
# 1. 外付けHDD マウント確認
df -h /mnt/backup-hdd
# Expected: 3.6TB の HDD がマウントされていること

# 2. Dockerコンテナ稼働確認
docker ps | grep mailserver
# Expected: mailserver-mariadb, mailserver-postfix, mailserver-dovecot が稼働中

# 3. プロジェクトディレクトリ確認
ls -la /opt/onprem-infra-system/project-root-infra/services/mailserver/
# Expected: data/, config/, docker-compose.yml が存在

# 4. ディスク容量確認
df -h /mnt/backup-hdd | awk 'NR==2 {print $5}' | sed 's/%//'
# Expected: 80 未満（使用率80%未満）
```

### 1.2 作業ディレクトリ移動

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
```

---

## 2. 必要なパッケージのインストール

```bash
# 2.1 バックアップツールのインストール
sudo dnf install -y rsync gzip tar coreutils findutils

# 2.2 MySQL クライアントのインストール（mysqldump用）
sudo dnf install -y mysql

# 2.3 メール送信用（通知）
sudo dnf install -y postfix
sudo systemctl enable --now postfix

# 2.4 cron のインストール（通常は既にインストール済み）
sudo dnf install -y cronie
sudo systemctl enable --now crond

# 2.5 インストール確認
rsync --version
mysqldump --version
tar --version
```

---

## 3. ディレクトリ構造の作成

### 3.1 バックアップ先ディレクトリ作成

```bash
# バックアップルートディレクトリ作成
sudo mkdir -p /mnt/backup-hdd/mailserver/{daily,weekly}

# パーミッション設定
sudo chown -R system-admin:system-admin /mnt/backup-hdd/mailserver
sudo chmod 700 /mnt/backup-hdd/mailserver

# 確認
ls -la /mnt/backup-hdd/mailserver/
```

### 3.2 スクリプトディレクトリ確認・作成

```bash
# スクリプトディレクトリ確認（既存）
ls -la /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/

# shared ディレクトリ作成（存在しない場合）
mkdir -p /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/shared
```

### 3.3 ログファイル確認

```bash
# ログファイルはユーザーホームディレクトリに自動作成されます
# ~/.mailserver-backup.log
# ~/.mailserver-backup-error.log
#
# 手動で作成する場合:
touch ~/.mailserver-backup.log
touch ~/.mailserver-backup-error.log
chmod 600 ~/.mailserver-backup*.log
```

---

## 4. 設定ファイルの作成

### 4.1 backup-config.sh の作成

```bash
cat > /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-config.sh << 'EOF'
#!/bin/bash
#
# backup-config.sh - Mailserver Backup Configuration
#

# ==================== Paths ====================
export PROJECT_ROOT="/opt/onprem-infra-system/project-root-infra"
export MAILSERVER_ROOT="${PROJECT_ROOT}/services/mailserver"
export BACKUP_ROOT="/mnt/backup-hdd/mailserver"
export SCRIPTS_DIR="${MAILSERVER_ROOT}/scripts"

# ==================== Backup Sources ====================
export MAIL_DATA_DIR="${MAILSERVER_ROOT}/data/mail"
export MYSQL_CONTAINER="mailserver-mariadb"
export MYSQL_DATABASES="usermgmt roundcubemail"
export CONFIG_DIR="${MAILSERVER_ROOT}/config"
export SSL_DIR="${MAILSERVER_ROOT}/data/certbot"
export DKIM_DIR="${CONFIG_DIR}/opendkim"
export DOCKER_COMPOSE_FILE="${MAILSERVER_ROOT}/docker-compose.yml"
export ENV_FILE="${MAILSERVER_ROOT}/.env"

# ==================== Backup Destinations ====================
export DAILY_BACKUP_DIR="${BACKUP_ROOT}/daily"
export WEEKLY_BACKUP_DIR="${BACKUP_ROOT}/weekly"
export LATEST_LINK="${BACKUP_ROOT}/latest"

# ==================== Retention ====================
export DAILY_RETENTION_DAYS=30
export WEEKLY_RETENTION_WEEKS=12

# ==================== Notifications ====================
export ADMIN_EMAIL="admin@example.com"
export NOTIFICATION_ON_SUCCESS=false
export NOTIFICATION_ON_FAILURE=true
export DISK_WARNING_THRESHOLD=80  # Percentage

# ==================== Logging ====================
export LOG_FILE="${LOG_FILE:-/home/system-admin/.mailserver-backup.log}"
export ERROR_LOG="${ERROR_LOG:-/home/system-admin/.mailserver-backup-error.log}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# ==================== Runtime ====================
export LOCK_FILE="/tmp/mailserver-backup.lock"
export TEMP_DIR="/tmp/mailserver-backup-$$"
export MAX_RETRIES=3
export RETRY_DELAY=10  # seconds

# ==================== MySQL Authentication ====================
# Use .my.cnf for secure password storage
export MYSQL_CONFIG_FILE="${HOME}/.my.cnf"
EOF

chmod 644 /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-config.sh
```

### 4.2 MySQL認証ファイルの作成

```bash
# .my.cnf 作成（system-admin ユーザーのホームディレクトリ）
cat > ~/.my.cnf << 'EOF'
[client]
user=root
password=YOUR_MYSQL_ROOT_PASSWORD_HERE
host=localhost
port=3306

[mysqldump]
user=root
password=YOUR_MYSQL_ROOT_PASSWORD_HERE
single-transaction
routines
triggers
EOF

# パーミッション設定（重要: 600 でないと危険）
chmod 600 ~/.my.cnf

# 確認
ls -la ~/.my.cnf
```

**重要**: `YOUR_MYSQL_ROOT_PASSWORD_HERE` を実際のMySQLのrootパスワードに置き換えてください。

**パスワードの確認方法**:
```bash
# .env ファイルから確認
grep MYSQL_ROOT_PASSWORD /opt/onprem-infra-system/project-root-infra/services/mailserver/.env
```

### 4.3 logrotate設定の作成

```bash
# logrotate 設定ファイル作成
sudo tee /etc/logrotate.d/mailserver-backup > /dev/null << 'EOF'
/home/system-admin/.mailserver-backup.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0600 system-admin system-admin
    su system-admin system-admin
}

/home/system-admin/.mailserver-backup-error.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0600 system-admin system-admin
    su system-admin system-admin
}
EOF

# 設定確認
sudo logrotate -d /etc/logrotate.d/mailserver-backup
```

---

## 5. バックアップスクリプトの実装

### 5.1 backup-mailserver.sh の作成

```bash
cat > /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-mailserver.sh << 'EOFSCRIPT'
#!/bin/bash
#
# backup-mailserver.sh - Dell Mailserver Backup Script
#
# Usage: ./backup-mailserver.sh [--daily|--weekly]
#

set -euo pipefail

# ==================== Configuration ====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/backup-config.sh"

# ==================== Global Variables ====================
BACKUP_TYPE="${1:-daily}"
BACKUP_DATE=$(date '+%Y-%m-%d')
BACKUP_TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
BACKUP_DIR=""
EXIT_CODE=0

# ==================== Logging Functions ====================
log() {
    local level="$1"
    local message="$2"
    local component="${3:-MAIN}"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    local log_entry="[${timestamp}] [${level}] [${component}] ${message}"

    # メインログに記録
    echo "${log_entry}" | tee -a "${LOG_FILE}"

    # エラーレベル以上はエラーログにも記録
    if [ "${level}" = "ERROR" ] || [ "${level}" = "CRITICAL" ]; then
        echo "${log_entry}" >> "${ERROR_LOG}"
    fi

    # CRITICAL は syslog にも記録
    if [ "${level}" = "CRITICAL" ]; then
        logger -t "mailserver-backup" -p user.crit "${message}"
    fi
}

# ==================== Utility Functions ====================
retry_command() {
    local max_attempts="${MAX_RETRIES}"
    local attempt=1
    local delay="${RETRY_DELAY}"

    while [ $attempt -le $max_attempts ]; do
        if "$@"; then
            return 0
        else
            log "ERROR" "Attempt $attempt/$max_attempts failed: $*"
            if [ $attempt -lt $max_attempts ]; then
                log "INFO" "Retrying in ${delay}s..."
                sleep $delay
                delay=$((delay * 2))  # Exponential backoff
            fi
            attempt=$((attempt + 1))
        fi
    done

    log "CRITICAL" "Command failed after $max_attempts attempts: $*"
    return 1
}

cleanup_on_exit() {
    log "INFO" "Cleaning up on exit..."
    if [ -f "${LOCK_FILE}" ]; then
        rm -f "${LOCK_FILE}"
    fi
    if [ -n "${TEMP_DIR:-}" ] && [ -d "${TEMP_DIR}" ]; then
        rm -rf "${TEMP_DIR}"
    fi
}

trap cleanup_on_exit EXIT
trap 'log "ERROR" "Script interrupted"; exit 130' INT TERM

# ==================== Core Functions ====================
initialize() {
    log "INFO" "Backup started" "INIT"
    log "INFO" "Backup type: ${BACKUP_TYPE}" "INIT"

    # 実行ユーザー確認
    if [ "$(id -u)" != "0" ] && [ "$(whoami)" != "system-admin" ]; then
        log "CRITICAL" "Must be run as root or system-admin" "INIT"
        return 1
    fi

    # ロックファイル確認（多重実行防止）
    if [ -f "${LOCK_FILE}" ]; then
        log "ERROR" "Another backup is running (lock file exists)" "INIT"
        return 1
    fi
    touch "${LOCK_FILE}"

    # 外付けHDD マウント確認
    if ! mountpoint -q /mnt/backup-hdd; then
        log "CRITICAL" "Backup HDD is not mounted at /mnt/backup-hdd" "INIT"
        return 1
    fi

    # ディスク容量確認
    local disk_usage=$(df -h /mnt/backup-hdd | awk 'NR==2 {print $5}' | sed 's/%//')
    log "INFO" "Disk usage: ${disk_usage}%" "INIT"

    if [ "${disk_usage}" -ge "${DISK_WARNING_THRESHOLD}" ]; then
        log "WARNING" "Disk usage is ${disk_usage}% (threshold: ${DISK_WARNING_THRESHOLD}%)" "INIT"
        send_disk_warning "${disk_usage}"
    fi

    # バックアップディレクトリ作成
    if [ "${BACKUP_TYPE}" = "daily" ]; then
        BACKUP_DIR="${DAILY_BACKUP_DIR}/${BACKUP_DATE}"
    else
        local week_num=$(date '+%Y-week-%U')
        BACKUP_DIR="${WEEKLY_BACKUP_DIR}/${week_num}"
    fi

    mkdir -p "${BACKUP_DIR}"/{mail,mysql,config,ssl,dkim}
    log "INFO" "Backup directory: ${BACKUP_DIR}" "INIT"

    return 0
}

backup_mail() {
    log "INFO" "Starting mail data backup" "MAIL"

    if [ ! -d "${MAIL_DATA_DIR}" ]; then
        log "ERROR" "Mail data directory not found: ${MAIL_DATA_DIR}" "MAIL"
        return 1
    fi

    # rsync オプション:
    # -a: アーカイブモード（パーミッション、タイムスタンプ保持）
    # -v: 詳細出力
    # -z: 圧縮転送（外付けHDDなので不要だが一応）
    # --delete: 送信元で削除されたファイルを削除
    # --exclude: 一時ファイル除外

    local rsync_opts=(
        -av
        --delete
        --exclude='*.tmp'
        --exclude='*.lock'
    )

    if retry_command rsync "${rsync_opts[@]}" "${MAIL_DATA_DIR}/" "${BACKUP_DIR}/mail/"; then
        local backup_size=$(du -sh "${BACKUP_DIR}/mail" | awk '{print $1}')
        log "INFO" "Mail backup completed: ${backup_size}" "MAIL"
        return 0
    else
        log "ERROR" "Mail backup failed" "MAIL"
        return 1
    fi
}

backup_mysql() {
    log "INFO" "Starting MySQL backup" "MYSQL"

    # Docker コンテナ稼働確認
    if ! docker ps | grep -q "${MYSQL_CONTAINER}"; then
        log "ERROR" "MySQL container not running: ${MYSQL_CONTAINER}" "MYSQL"
        return 1
    fi

    # 各データベースをバックアップ
    for db in ${MYSQL_DATABASES}; do
        log "INFO" "Backing up database: ${db}" "MYSQL"

        local dump_file="${BACKUP_DIR}/mysql/${db}.sql"
        local gzip_file="${dump_file}.gz"

        # mysqldump 実行（コンテナ内で実行）
        if retry_command docker exec "${MYSQL_CONTAINER}" mysqldump \
            --defaults-extra-file=/root/.my.cnf \
            --single-transaction \
            --routines \
            --triggers \
            "${db}" > "${dump_file}"; then

            # gzip 圧縮
            gzip "${dump_file}"

            # 圧縮ファイル検証
            if gzip -t "${gzip_file}" 2>/dev/null; then
                local backup_size=$(du -sh "${gzip_file}" | awk '{print $1}')
                log "INFO" "Database ${db} backup completed: ${backup_size}" "MYSQL"
            else
                log "ERROR" "Database ${db} backup verification failed" "MYSQL"
                return 1
            fi
        else
            log "ERROR" "Database ${db} backup failed" "MYSQL"
            return 1
        fi
    done

    return 0
}

backup_config() {
    log "INFO" "Starting config backup" "CONFIG"

    # 設定ディレクトリの tar アーカイブ
    if [ -d "${CONFIG_DIR}" ]; then
        if tar -czf "${BACKUP_DIR}/config/config.tar.gz" -C "${MAILSERVER_ROOT}" config/; then
            log "INFO" "Config directory backed up" "CONFIG"
        else
            log "ERROR" "Config backup failed" "CONFIG"
            return 1
        fi
    fi

    # docker-compose.yml コピー
    if [ -f "${DOCKER_COMPOSE_FILE}" ]; then
        cp "${DOCKER_COMPOSE_FILE}" "${BACKUP_DIR}/config/"
        log "INFO" "docker-compose.yml backed up" "CONFIG"
    fi

    # .env コピー（機密情報注意）
    if [ -f "${ENV_FILE}" ]; then
        cp "${ENV_FILE}" "${BACKUP_DIR}/config/"
        chmod 600 "${BACKUP_DIR}/config/.env"
        log "INFO" ".env backed up" "CONFIG"
    fi

    return 0
}

backup_ssl() {
    log "INFO" "Starting SSL backup" "SSL"

    if [ -d "${SSL_DIR}" ]; then
        if tar -czf "${BACKUP_DIR}/ssl/certbot.tar.gz" -C "${MAILSERVER_ROOT}/data" certbot/; then
            log "INFO" "SSL certificates backed up" "SSL"
            return 0
        else
            log "ERROR" "SSL backup failed" "SSL"
            return 1
        fi
    else
        log "WARNING" "SSL directory not found: ${SSL_DIR}" "SSL"
        return 0
    fi
}

backup_dkim() {
    log "INFO" "Starting DKIM backup" "DKIM"

    if [ -d "${DKIM_DIR}" ]; then
        if tar -czf "${BACKUP_DIR}/dkim/opendkim-keys.tar.gz" -C "${CONFIG_DIR}" opendkim/; then
            log "INFO" "DKIM keys backed up" "DKIM"
            return 0
        else
            log "ERROR" "DKIM backup failed" "DKIM"
            return 1
        fi
    else
        log "WARNING" "DKIM directory not found: ${DKIM_DIR}" "DKIM"
        return 0
    fi
}

verify_backup() {
    log "INFO" "Starting backup verification" "VERIFY"

    # ディレクトリ存在確認
    for dir in mail mysql config ssl dkim; do
        if [ ! -d "${BACKUP_DIR}/${dir}" ]; then
            log "ERROR" "Backup directory missing: ${dir}" "VERIFY"
            return 1
        fi
    done

    # ファイル数カウント
    local file_count=$(find "${BACKUP_DIR}" -type f | wc -l)
    log "INFO" "Total files backed up: ${file_count}" "VERIFY"

    # 合計サイズ計算
    local total_size=$(du -sh "${BACKUP_DIR}" | awk '{print $1}')
    log "INFO" "Total backup size: ${total_size}" "VERIFY"

    # チェックサム生成
    log "INFO" "Generating checksums..." "VERIFY"
    find "${BACKUP_DIR}" -type f -exec sha256sum {} \; > "${BACKUP_DIR}/checksums.sha256"

    # バックアップログ保存
    cp "${LOG_FILE}" "${BACKUP_DIR}/backup.log"

    # latest シンボリックリンク更新
    rm -f "${LATEST_LINK}"
    ln -s "${BACKUP_DIR}" "${LATEST_LINK}"

    log "INFO" "Backup verification completed" "VERIFY"
    return 0
}

cleanup_old() {
    log "INFO" "Starting cleanup of old backups" "CLEANUP"

    # 日次バックアップ削除（30日超過）
    log "INFO" "Cleaning up daily backups older than ${DAILY_RETENTION_DAYS} days" "CLEANUP"
    find "${DAILY_BACKUP_DIR}" -maxdepth 1 -type d -mtime +${DAILY_RETENTION_DAYS} -exec rm -rf {} \; 2>/dev/null || true

    # 週次バックアップ削除（12週超過 = 84日）
    local weekly_retention_days=$((WEEKLY_RETENTION_WEEKS * 7))
    log "INFO" "Cleaning up weekly backups older than ${WEEKLY_RETENTION_WEEKS} weeks" "CLEANUP"
    find "${WEEKLY_BACKUP_DIR}" -maxdepth 1 -type d -mtime +${weekly_retention_days} -exec rm -rf {} \; 2>/dev/null || true

    # ディスク容量再確認
    local disk_usage=$(df -h /mnt/backup-hdd | awk 'NR==2 {print $5}' | sed 's/%//')
    log "INFO" "Disk usage after cleanup: ${disk_usage}%" "CLEANUP"

    return 0
}

send_notification() {
    local status="$1"
    local message="$2"

    if [ "${status}" = "success" ] && [ "${NOTIFICATION_ON_SUCCESS}" != "true" ]; then
        return 0
    fi

    if [ "${status}" = "failure" ] && [ "${NOTIFICATION_ON_FAILURE}" != "true" ]; then
        return 0
    fi

    local subject
    local priority

    if [ "${status}" = "success" ]; then
        subject="[INFO] Mailserver Backup Succeeded - ${BACKUP_DATE}"
        priority="normal"
    else
        subject="[ALERT] Mailserver Backup Failed - ${BACKUP_DATE}"
        priority="high"
    fi

    local email_body
    email_body=$(cat <<EOF
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Dell Mailserver Backup Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Backup Date: ${BACKUP_TIMESTAMP}
Status: ${status^^}
Backup Type: ${BACKUP_TYPE}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Details
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

${message}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Logs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Full logs: ${LOG_FILE}
Error logs: ${ERROR_LOG}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
)

    echo "${email_body}" | mail -s "${subject}" "${ADMIN_EMAIL}"
    log "INFO" "Notification sent to ${ADMIN_EMAIL}" "NOTIFY"
}

send_disk_warning() {
    local usage="$1"

    local subject="[WARNING] Backup Disk Capacity at ${usage}%"

    local email_body
    email_body=$(cat <<EOF
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Backup Disk Capacity Warning
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Mount Point: /mnt/backup-hdd
Usage: ${usage}%
Threshold: ${DISK_WARNING_THRESHOLD}%

$(df -h /mnt/backup-hdd)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Recommendations
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Review and delete unnecessary backups
2. Consider reducing retention period
3. Plan for disk upgrade or additional storage

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
)

    echo "${email_body}" | mail -s "${subject}" "${ADMIN_EMAIL}"
    log "INFO" "Disk warning sent to ${ADMIN_EMAIL}" "NOTIFY"
}

# ==================== Main Function ====================
main() {
    local start_time=$(date +%s)

    # 初期化
    if ! initialize; then
        EXIT_CODE=2
        return ${EXIT_CODE}
    fi

    # バックアップ実行
    local failed_components=()

    if ! backup_mail; then
        failed_components+=("mail")
        EXIT_CODE=1
    fi

    if ! backup_mysql; then
        failed_components+=("mysql")
        EXIT_CODE=1
    fi

    if ! backup_config; then
        failed_components+=("config")
        EXIT_CODE=1
    fi

    if ! backup_ssl; then
        failed_components+=("ssl")
        EXIT_CODE=1
    fi

    if ! backup_dkim; then
        failed_components+=("dkim")
        EXIT_CODE=1
    fi

    # 検証
    if ! verify_backup; then
        EXIT_CODE=1
    fi

    # クリーンアップ
    cleanup_old

    # 実行時間計算
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local duration_min=$((duration / 60))

    log "INFO" "Backup completed in ${duration_min} minutes" "MAIN"

    # 通知送信
    if [ ${EXIT_CODE} -eq 0 ]; then
        local total_size=$(du -sh "${BACKUP_DIR}" | awk '{print $1}')
        send_notification "success" "All components backed up successfully. Total size: ${total_size}"
    else
        local failure_msg="Failed components: ${failed_components[*]}"
        send_notification "failure" "${failure_msg}"
    fi

    return ${EXIT_CODE}
}

# ==================== Entry Point ====================
main "$@"
EOFSCRIPT

# 実行権限付与
chmod 750 /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-mailserver.sh
```

**スクリプト確認**:
```bash
ls -la /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-mailserver.sh
# Expected: -rwxr-x--- 1 system-admin system-admin
```

---

## 6. cron設定

### 6.1 cron ジョブの追加

```bash
# crontab 編集
crontab -e

# 以下を追加:
# 毎日午前3時に日次バックアップ実行
0 3 * * * /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-mailserver.sh --daily >> ~/.mailserver-backup.log 2>&1

# 毎週日曜日午前4時に週次バックアップ実行
0 4 * * 0 /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-mailserver.sh --weekly >> ~/.mailserver-backup.log 2>&1
```

### 6.2 cron 設定確認

```bash
# crontab 確認
crontab -l

# cron サービス稼働確認
sudo systemctl status crond

# cron ログ確認
sudo tail -f /var/log/cron
```

---

## 7. 初回実行とテスト

### 7.1 手動実行テスト

```bash
# 日次バックアップを手動実行
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts
./backup-mailserver.sh --daily

# 実行結果確認
echo $?
# Expected: 0 (成功)

# ログ確認
tail -n 50 ~/.mailserver-backup.log

# バックアップディレクトリ確認
ls -la /mnt/backup-hdd/mailserver/daily/$(date '+%Y-%m-%d')/

# バックアップサイズ確認
du -sh /mnt/backup-hdd/mailserver/daily/$(date '+%Y-%m-%d')
```

### 7.2 各コンポーネントの検証

```bash
# メールデータ確認
ls -la /mnt/backup-hdd/mailserver/daily/$(date '+%Y-%m-%d')/mail/vmail/

# MySQLダンプ確認
ls -la /mnt/backup-hdd/mailserver/daily/$(date '+%Y-%m-%d')/mysql/
gunzip -t /mnt/backup-hdd/mailserver/daily/$(date '+%Y-%m-%d')/mysql/*.sql.gz

# 設定ファイル確認
tar -tzf /mnt/backup-hdd/mailserver/daily/$(date '+%Y-%m-%d')/config/config.tar.gz | head

# SSL証明書確認
tar -tzf /mnt/backup-hdd/mailserver/daily/$(date '+%Y-%m-%d')/ssl/certbot.tar.gz | head

# チェックサム確認
head /mnt/backup-hdd/mailserver/daily/$(date '+%Y-%m-%d')/checksums.sha256
```

### 7.3 リカバリーテスト（テスト環境推奨）

```bash
# テスト用ディレクトリ作成
mkdir -p /tmp/restore-test

# メールデータのリストアテスト
rsync -av /mnt/backup-hdd/mailserver/latest/mail/ /tmp/restore-test/mail/

# MySQLダンプのリストアテスト（dry-run）
gunzip -c /mnt/backup-hdd/mailserver/latest/mysql/usermgmt.sql.gz | head -n 20

# 設定ファイルのリストアテスト
tar -xzf /mnt/backup-hdd/mailserver/latest/config/config.tar.gz -C /tmp/restore-test/

# テストディレクトリ削除
rm -rf /tmp/restore-test
```

---

## 8. リストアスクリプトの実装

### 8.1 restore-mailserver.sh の作成

```bash
cat > /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/restore-mailserver.sh << 'EOFSCRIPT'
#!/bin/bash
#
# restore-mailserver.sh - Mailserver Restore Script
#
# Usage: ./restore-mailserver.sh --from /mnt/backup-hdd/mailserver/latest [--component mail|mysql|config|ssl|dkim|all]
#

set -euo pipefail

# ==================== Configuration ====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/backup-config.sh"

# ==================== Global Variables ====================
BACKUP_SOURCE=""
COMPONENT="all"

# ==================== Functions ====================
usage() {
    cat <<EOF
Usage: $0 --from BACKUP_PATH [--component COMPONENT]

Options:
  --from PATH       Path to backup directory (e.g., /mnt/backup-hdd/mailserver/latest)
  --component NAME  Component to restore: mail|mysql|config|ssl|dkim|all (default: all)

Examples:
  # Restore all components
  $0 --from /mnt/backup-hdd/mailserver/latest

  # Restore only mail data
  $0 --from /mnt/backup-hdd/mailserver/daily/2025-11-06 --component mail

  # Restore only MySQL
  $0 --from /mnt/backup-hdd/mailserver/latest --component mysql
EOF
    exit 1
}

log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}"
}

validate_backup() {
    log "INFO" "Validating backup source: ${BACKUP_SOURCE}"

    if [ ! -d "${BACKUP_SOURCE}" ]; then
        log "ERROR" "Backup directory not found: ${BACKUP_SOURCE}"
        return 1
    fi

    # チェックサムファイル存在確認
    if [ -f "${BACKUP_SOURCE}/checksums.sha256" ]; then
        log "INFO" "Checksum file found, verifying..."
        if (cd "${BACKUP_SOURCE}" && sha256sum -c checksums.sha256 >/dev/null 2>&1); then
            log "INFO" "Backup integrity verified"
        else
            log "WARNING" "Checksum verification failed, but continuing..."
        fi
    else
        log "WARNING" "Checksum file not found"
    fi

    return 0
}

restore_mail() {
    log "INFO" "Restoring mail data..."

    if [ ! -d "${BACKUP_SOURCE}/mail" ]; then
        log "ERROR" "Mail backup not found in ${BACKUP_SOURCE}"
        return 1
    fi

    # バックアップ作成（既存データ保護）
    if [ -d "${MAIL_DATA_DIR}" ]; then
        local backup_ts=$(date '+%Y%m%d_%H%M%S')
        log "INFO" "Creating backup of existing mail data..."
        mv "${MAIL_DATA_DIR}" "${MAIL_DATA_DIR}.bak.${backup_ts}"
    fi

    # rsync でリストア
    mkdir -p "${MAIL_DATA_DIR}"
    rsync -av "${BACKUP_SOURCE}/mail/" "${MAIL_DATA_DIR}/"

    # パーミッション修正
    chown -R 5000:5000 "${MAIL_DATA_DIR}"

    log "INFO" "Mail data restored successfully"
    return 0
}

restore_mysql() {
    log "INFO" "Restoring MySQL databases..."

    if [ ! -d "${BACKUP_SOURCE}/mysql" ]; then
        log "ERROR" "MySQL backup not found in ${BACKUP_SOURCE}"
        return 1
    fi

    # Docker コンテナ稼働確認
    if ! docker ps | grep -q "${MYSQL_CONTAINER}"; then
        log "ERROR" "MySQL container not running: ${MYSQL_CONTAINER}"
        return 1
    fi

    # 各データベースをリストア
    for db in ${MYSQL_DATABASES}; do
        local dump_file="${BACKUP_SOURCE}/mysql/${db}.sql.gz"

        if [ -f "${dump_file}" ]; then
            log "INFO" "Restoring database: ${db}"
            gunzip -c "${dump_file}" | docker exec -i "${MYSQL_CONTAINER}" mysql -u root -p"${MYSQL_ROOT_PASSWORD}" "${db}"
            log "INFO" "Database ${db} restored"
        else
            log "WARNING" "Database dump not found: ${dump_file}"
        fi
    done

    return 0
}

restore_config() {
    log "INFO" "Restoring configuration files..."

    if [ ! -d "${BACKUP_SOURCE}/config" ]; then
        log "ERROR" "Config backup not found in ${BACKUP_SOURCE}"
        return 1
    fi

    # 設定ファイルの展開
    if [ -f "${BACKUP_SOURCE}/config/config.tar.gz" ]; then
        tar -xzf "${BACKUP_SOURCE}/config/config.tar.gz" -C "${MAILSERVER_ROOT}/"
        log "INFO" "Config files restored"
    fi

    # docker-compose.yml リストア
    if [ -f "${BACKUP_SOURCE}/config/docker-compose.yml" ]; then
        cp "${BACKUP_SOURCE}/config/docker-compose.yml" "${DOCKER_COMPOSE_FILE}"
        log "INFO" "docker-compose.yml restored"
    fi

    # .env リストア
    if [ -f "${BACKUP_SOURCE}/config/.env" ]; then
        cp "${BACKUP_SOURCE}/config/.env" "${ENV_FILE}"
        chmod 600 "${ENV_FILE}"
        log "INFO" ".env restored"
    fi

    return 0
}

restore_ssl() {
    log "INFO" "Restoring SSL certificates..."

    if [ ! -d "${BACKUP_SOURCE}/ssl" ]; then
        log "ERROR" "SSL backup not found in ${BACKUP_SOURCE}"
        return 1
    fi

    if [ -f "${BACKUP_SOURCE}/ssl/certbot.tar.gz" ]; then
        tar -xzf "${BACKUP_SOURCE}/ssl/certbot.tar.gz" -C "${MAILSERVER_ROOT}/data/"
        log "INFO" "SSL certificates restored"
    fi

    return 0
}

restore_dkim() {
    log "INFO" "Restoring DKIM keys..."

    if [ ! -d "${BACKUP_SOURCE}/dkim" ]; then
        log "ERROR" "DKIM backup not found in ${BACKUP_SOURCE}"
        return 1
    fi

    if [ -f "${BACKUP_SOURCE}/dkim/opendkim-keys.tar.gz" ]; then
        tar -xzf "${BACKUP_SOURCE}/dkim/opendkim-keys.tar.gz" -C "${CONFIG_DIR}/"
        log "INFO" "DKIM keys restored"
    fi

    return 0
}

restart_services() {
    log "INFO" "Restarting Docker Compose services..."
    cd "${MAILSERVER_ROOT}"
    docker compose restart
    log "INFO" "Services restarted"
}

# ==================== Main Function ====================
main() {
    # 引数解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            --from)
                BACKUP_SOURCE="$2"
                shift 2
                ;;
            --component)
                COMPONENT="$2"
                shift 2
                ;;
            -h|--help)
                usage
                ;;
            *)
                log "ERROR" "Unknown option: $1"
                usage
                ;;
        esac
    done

    # 必須パラメータ確認
    if [ -z "${BACKUP_SOURCE}" ]; then
        log "ERROR" "--from option is required"
        usage
    fi

    # バックアップ検証
    if ! validate_backup; then
        return 1
    fi

    # コンポーネントリストア
    case "${COMPONENT}" in
        mail)
            restore_mail
            ;;
        mysql)
            restore_mysql
            ;;
        config)
            restore_config
            ;;
        ssl)
            restore_ssl
            ;;
        dkim)
            restore_dkim
            ;;
        all)
            restore_config
            restore_mail
            restore_ssl
            restore_dkim
            restart_services
            restore_mysql
            ;;
        *)
            log "ERROR" "Unknown component: ${COMPONENT}"
            usage
            ;;
    esac

    log "INFO" "Restore completed"
    return 0
}

# ==================== Entry Point ====================
main "$@"
EOFSCRIPT

# 実行権限付与
chmod 750 /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/restore-mailserver.sh
```

---

## 9. トラブルシューティング

### 9.1 よくある問題と対処法

#### 問題1: バックアップが失敗する

**症状**:
```
[ERROR] [MYSQL] mysqldump failed: connection lost
```

**原因と対処**:
1. MySQL コンテナが停止している
   ```bash
   docker ps | grep mailserver-mariadb
   docker compose -f /opt/onprem-infra-system/project-root-infra/services/mailserver/docker-compose.yml up -d mailserver-mariadb
   ```

2. MySQL認証情報が間違っている
   ```bash
   # ~/.my.cnf のパスワード確認
   docker exec mailserver-mariadb mysql -u root -p
   ```

#### 問題2: ディスク容量不足

**症状**:
```
[ERROR] No space left on device
```

**対処**:
```bash
# ディスク使用状況確認
df -h /mnt/backup-hdd

# 古いバックアップ手動削除
find /mnt/backup-hdd/mailserver/daily -type d -mtime +30 -exec rm -rf {} \;

# 保存期間短縮（backup-config.sh編集）
# DAILY_RETENTION_DAYS を 30 → 15 に変更
```

#### 問題3: rsync が遅い

**症状**:
バックアップに1時間以上かかる

**対処**:
```bash
# rsync オプション調整（圧縮無効化）
# backup-mailserver.sh の rsync_opts を編集:
# -avz → -av に変更（圧縮無効）

# I/O優先度を下げる
ionice -c3 nice -n19 ./backup-mailserver.sh --daily
```

#### 問題4: メール通知が届かない

**症状**:
バックアップ失敗時にメールが届かない

**対処**:
```bash
# Postfix 稼働確認
sudo systemctl status postfix

# メールキュー確認
mailq

# テストメール送信
echo "Test" | mail -s "Test" admin@example.com

# Postfix ログ確認
sudo tail -f /var/log/maillog
```

### 9.2 診断コマンド

```bash
# 1. バックアップスクリプト構文チェック
bash -n /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-mailserver.sh

# 2. 設定ファイル確認
cat /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-config.sh

# 3. 最新バックアップ確認
ls -la /mnt/backup-hdd/mailserver/latest/

# 4. ログ確認
tail -n 100 ~/.mailserver-backup.log
tail -n 100 ~/.mailserver-backup-error.log

# 5. cron 実行履歴確認
sudo grep "backup-mailserver" /var/log/cron

# 6. ディスク容量確認
df -h /mnt/backup-hdd
du -sh /mnt/backup-hdd/mailserver/*

# 7. プロセス確認（実行中の場合）
ps aux | grep backup-mailserver

# 8. ロックファイル確認
ls -la /var/run/mailserver-backup.lock
```

### 9.3 緊急時の手動バックアップ

```bash
# 完全な手動バックアップ（スクリプトを使わない）
BACKUP_DATE=$(date '+%Y-%m-%d')
BACKUP_DIR="/mnt/backup-hdd/mailserver/manual/${BACKUP_DATE}"
mkdir -p "${BACKUP_DIR}"

# メールデータ
rsync -av /opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail/ "${BACKUP_DIR}/mail/"

# MySQL
docker exec mailserver-mariadb mysqldump -u root -p usermgmt | gzip > "${BACKUP_DIR}/usermgmt.sql.gz"
docker exec mailserver-mariadb mysqldump -u root -p roundcubemail | gzip > "${BACKUP_DIR}/roundcubemail.sql.gz"

# 設定
tar -czf "${BACKUP_DIR}/config.tar.gz" -C /opt/onprem-infra-system/project-root-infra/services/mailserver config/
```

---

## 📝 付録

### A. チェックリスト

**実装完了チェックリスト**:

- [ ] 必要なパッケージがインストールされている
- [ ] バックアップディレクトリが作成されている
- [ ] backup-config.sh が作成・設定されている
- [ ] ~/.my.cnf が作成・設定されている（パーミッション 600）
- [ ] backup-mailserver.sh が作成されている（実行権限あり）
- [ ] restore-mailserver.sh が作成されている（実行権限あり）
- [ ] logrotate 設定が作成されている
- [ ] cron ジョブが設定されている
- [ ] 手動テスト実行が成功している
- [ ] バックアップデータの検証が成功している
- [ ] リカバリーテストが成功している

**運用チェックリスト（定期実施）**:

- [ ] 日次: バックアップログ確認
- [ ] 週次: ディスク容量確認
- [ ] 月次: バックアップ検証（チェックサム）
- [ ] 四半期: リカバリーテスト実施

### B. 関連ドキュメント

- [01_requirements.md](./01_requirements.md) - 要件定義書
- [02_design.md](./02_design.md) - 設計書
- [Mailserver README](../README.md) - Mailserver全体ドキュメント

### C. 変更履歴

| バージョン | 日付 | 変更内容 | 作成者 |
|----------|------|---------|--------|
| 1.0 | 2025-11-07 | 初版作成 | system-admin |
| 1.1 | 2025-11-07 | コンテナ名修正、スクリプト実装完了 | system-admin |

---

**END OF DOCUMENT**
