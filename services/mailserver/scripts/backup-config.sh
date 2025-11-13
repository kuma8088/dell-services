#!/bin/bash
#
# backup-config.sh - Mailserver Backup Configuration
# Version: 1.2
#
# Changelog:
# - v1.2 (2025-11-07): Added Phase 11-B S3 backup configuration support
#                      Added AWS environment variables, S3_BUCKET auto-config
#                      Added log() and check_lock_file() helper functions
# - v1.1 (2025-11-07): Fixed LOG_FILE/ERROR_LOG to use absolute path
#                      /home/system-admin/ instead of ${HOME} to ensure
#                      consistent log location regardless of execution user
#

set -euo pipefail

# ==================== Paths ====================
: "${PROJECT_ROOT:=/opt/onprem-infra-system/project-root-infra}"
export PROJECT_ROOT
: "${MAILSERVER_ROOT:=${PROJECT_ROOT}/services/mailserver}"
export MAILSERVER_ROOT
: "${BACKUP_ROOT:=/mnt/backup-hdd/rental/mail}"
export BACKUP_ROOT
: "${BACKUP_MOUNTPOINT:=/mnt/backup-hdd}"
export BACKUP_MOUNTPOINT
: "${SCRIPTS_DIR:=${MAILSERVER_ROOT}/scripts}"
export SCRIPTS_DIR

# ==================== Backup Sources ====================
: "${MAIL_DATA_DIR:=${MAILSERVER_ROOT}/data/mail}"
export MAIL_DATA_DIR
: "${MYSQL_CONTAINER:=mailserver-mariadb}"
export MYSQL_CONTAINER
: "${MYSQL_USER:=root}"
export MYSQL_USER
: "${MYSQL_DATABASES:=mailserver_usermgmt roundcube_mailserver}"
export MYSQL_DATABASES
: "${CONFIG_DIR:=${MAILSERVER_ROOT}/config}"
export CONFIG_DIR
: "${SSL_DIR:=${MAILSERVER_ROOT}/data/certbot}"
export SSL_DIR
: "${DKIM_DIR:=${CONFIG_DIR}/opendkim}"
export DKIM_DIR
: "${DOCKER_COMPOSE_FILE:=${MAILSERVER_ROOT}/docker-compose.yml}"
export DOCKER_COMPOSE_FILE
: "${ENV_FILE:=${MAILSERVER_ROOT}/.env}"
export ENV_FILE

# ==================== Backup Destinations ====================
: "${DAILY_BACKUP_DIR:=${BACKUP_ROOT}/daily}"
export DAILY_BACKUP_DIR
: "${WEEKLY_BACKUP_DIR:=${BACKUP_ROOT}/weekly}"
export WEEKLY_BACKUP_DIR
: "${LATEST_LINK:=${BACKUP_ROOT}/latest}"
export LATEST_LINK

# ==================== Retention ====================
export DAILY_RETENTION_DAYS="${DAILY_RETENTION_DAYS:-30}"
export WEEKLY_RETENTION_WEEKS="${WEEKLY_RETENTION_WEEKS:-12}"

# ==================== Notifications ====================
: "${ADMIN_EMAIL:=naoya.iimura@gmail.com}"
export ADMIN_EMAIL
: "${NOTIFICATION_ON_SUCCESS:=false}"
export NOTIFICATION_ON_SUCCESS
: "${NOTIFICATION_ON_FAILURE:=true}"
export NOTIFICATION_ON_FAILURE
: "${DISK_WARNING_THRESHOLD:=80}"
export DISK_WARNING_THRESHOLD

# ==================== Logging ====================
: "${LOG_FILE:=/home/system-admin/.mailserver-backup.log}"
export LOG_FILE
: "${ERROR_LOG:=/home/system-admin/.mailserver-backup-error.log}"
export ERROR_LOG
: "${LOG_LEVEL:=INFO}"
export LOG_LEVEL

# ==================== Runtime ====================
: "${LOCK_FILE:=/tmp/mailserver-backup.lock}"
export LOCK_FILE
: "${TEMP_DIR:=/tmp/mailserver-backup-$$}"
export TEMP_DIR
: "${MAX_RETRIES:=3}"
export MAX_RETRIES
: "${RETRY_DELAY:=10}"
export RETRY_DELAY

# ==================== MySQL Authentication ====================
# Use .my.cnf for secure password storage
: "${MYSQL_CONFIG_FILE:=${HOME}/.my.cnf}"
export MYSQL_CONFIG_FILE

# ==================== Phase 11-B: S3 Backup Configuration ====================

# Load S3-specific configuration if exists
S3_CONFIG_FILE="${S3_CONFIG_FILE:-/etc/mailserver-backup/config}"

if [ -f "$S3_CONFIG_FILE" ]; then
    # shellcheck source=/dev/null
    source "$S3_CONFIG_FILE"

    # Validate required AWS configuration
    if [ -n "${AWS_PROFILE:-}" ]; then
        export AWS_PROFILE
    fi

    if [ -n "${AWS_DEFAULT_REGION:-}" ]; then
        export AWS_DEFAULT_REGION
    fi

    # Get AWS Account ID if AWS is configured
    if [ -n "${AWS_PROFILE:-}" ] && [ -n "${AWS_DEFAULT_REGION:-}" ]; then
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")

        if [ -n "$AWS_ACCOUNT_ID" ]; then
            # Auto-configure S3 bucket name
            export S3_BUCKET="${S3_BUCKET:-mailserver-backup-${AWS_ACCOUNT_ID}}"
            export AWS_ACCOUNT_ID
        fi
    fi
fi

# ==================== Helper Functions ====================

# log() - Write log message to file and stdout
# Usage: log "message"
log() {
    local message="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # Write to log file
    echo "[${timestamp}] ${message}" >> "$LOG_FILE"

    # Write to stdout
    echo "[${timestamp}] ${message}"
}

# check_lock_file() - Check if backup is already running
# Returns: 0 if no lock, 1 if locked
check_lock_file() {
    if [ -f "$LOCK_FILE" ]; then
        local pid
        pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")

        # Check if process is still running
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            log "ERROR: Backup already running (PID: ${pid})"
            return 1
        else
            # Stale lock file, remove it
            log "WARNING: Removing stale lock file"
            rm -f "$LOCK_FILE"
            return 0
        fi
    fi

    return 0
}

# create_lock_file() - Create lock file with current PID
create_lock_file() {
    echo $$ > "$LOCK_FILE"
    log "Created lock file: $LOCK_FILE"
}

# remove_lock_file() - Remove lock file
remove_lock_file() {
    if [ -f "$LOCK_FILE" ]; then
        rm -f "$LOCK_FILE"
        log "Removed lock file: $LOCK_FILE"
    fi
}
