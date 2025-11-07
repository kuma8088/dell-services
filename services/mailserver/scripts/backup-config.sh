#!/bin/bash
#
# backup-config.sh - Mailserver Backup Configuration
# Version: 1.1
#
# Changelog:
# - v1.1 (2025-11-07): Fixed LOG_FILE/ERROR_LOG to use absolute path
#                      /home/system-admin/ instead of ${HOME} to ensure
#                      consistent log location regardless of execution user
#

# ==================== Paths ====================
export PROJECT_ROOT="/opt/onprem-infra-system/project-root-infra"
export MAILSERVER_ROOT="${PROJECT_ROOT}/services/mailserver"
export BACKUP_ROOT="/mnt/backup-hdd/mailserver"
export SCRIPTS_DIR="${MAILSERVER_ROOT}/scripts"

# ==================== Backup Sources ====================
export MAIL_DATA_DIR="${MAILSERVER_ROOT}/data/mail"
export MYSQL_CONTAINER="${MYSQL_CONTAINER:-mailserver-mariadb}"
export MYSQL_USER="${MYSQL_USER:-root}"
export MYSQL_DATABASES="${MYSQL_DATABASES:-mailserver_usermgmt roundcube_mailserver}"
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
export DAILY_RETENTION_DAYS="${DAILY_RETENTION_DAYS:-30}"
export WEEKLY_RETENTION_WEEKS="${WEEKLY_RETENTION_WEEKS:-12}"

# ==================== Notifications ====================
export ADMIN_EMAIL="${ADMIN_EMAIL:-naoya.iimura@gmail.com}"
export NOTIFICATION_ON_SUCCESS="${NOTIFICATION_ON_SUCCESS:-false}"
export NOTIFICATION_ON_FAILURE="${NOTIFICATION_ON_FAILURE:-true}"
export DISK_WARNING_THRESHOLD="${DISK_WARNING_THRESHOLD:-80}" # Percentage

# ==================== Logging ====================
export LOG_FILE="${LOG_FILE:-/home/system-admin/.mailserver-backup.log}"
export ERROR_LOG="${ERROR_LOG:-/home/system-admin/.mailserver-backup-error.log}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# ==================== Runtime ====================
export LOCK_FILE="${LOCK_FILE:-/tmp/mailserver-backup.lock}"
export TEMP_DIR="${TEMP_DIR:-/tmp/mailserver-backup-$$}"
export MAX_RETRIES="${MAX_RETRIES:-3}"
export RETRY_DELAY="${RETRY_DELAY:-10}" # seconds

# ==================== MySQL Authentication ====================
# Use .my.cnf for secure password storage
export MYSQL_CONFIG_FILE="${MYSQL_CONFIG_FILE:-${HOME}/.my.cnf}"
