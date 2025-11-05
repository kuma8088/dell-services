#!/bin/bash
#
# Mailserver Backup Script
# Phase 9: Production Deployment Preparation
#
# Purpose: Comprehensive backup of mailserver infrastructure
# - MariaDB databases (usermgmt, roundcube)
# - Configuration files (dovecot, postfix, nginx, roundcube, usermgmt)
# - Docker compose configurations
# - Mail data (optional, large volume)
#
# Usage: ./backup-mailserver.sh [--include-mail-data]
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_ROOT="${PROJECT_ROOT}/backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"

# Include mail data in backup (large, optional)
INCLUDE_MAIL_DATA=false
if [[ "${1:-}" == "--include-mail-data" ]]; then
    INCLUDE_MAIL_DATA=true
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create backup directory
create_backup_dir() {
    log_info "Creating backup directory: ${BACKUP_DIR}"
    mkdir -p "${BACKUP_DIR}"/{database,config,docker,logs}
}

# Backup MariaDB databases
backup_databases() {
    log_info "Backing up MariaDB databases..."

    # Load DB password from .env
    if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
        log_error ".env file not found at ${PROJECT_ROOT}/.env"
        return 1
    fi

    # shellcheck disable=SC1091
    source "${PROJECT_ROOT}/.env"

    # Backup usermgmt database
    log_info "  - Backing up mailserver_usermgmt database..."
    docker exec mailserver-mariadb mysqldump \
        -u root \
        -p"${MYSQL_ROOT_PASSWORD}" \
        --single-transaction \
        --routines \
        --triggers \
        --events \
        mailserver_usermgmt \
        > "${BACKUP_DIR}/database/mailserver_usermgmt.sql"

    # Backup roundcube database
    log_info "  - Backing up ${MYSQL_DATABASE} database..."
    docker exec mailserver-mariadb mysqldump \
        -u root \
        -p"${MYSQL_ROOT_PASSWORD}" \
        --single-transaction \
        --routines \
        --triggers \
        --events \
        "${MYSQL_DATABASE}" \
        > "${BACKUP_DIR}/database/${MYSQL_DATABASE}.sql"

    # Compress database backups
    log_info "  - Compressing database backups..."
    gzip "${BACKUP_DIR}/database/"*.sql

    log_info "Database backup completed"
}

# Backup configuration files
backup_configs() {
    log_info "Backing up configuration files..."

    # Dovecot configuration
    if [[ -d "${PROJECT_ROOT}/config/dovecot" ]]; then
        log_info "  - Backing up Dovecot configuration..."
        tar -czf "${BACKUP_DIR}/config/dovecot_config.tar.gz" \
            -C "${PROJECT_ROOT}/config" dovecot
    fi

    # Postfix configuration
    if [[ -d "${PROJECT_ROOT}/config/postfix" ]]; then
        log_info "  - Backing up Postfix configuration..."
        tar -czf "${BACKUP_DIR}/config/postfix_config.tar.gz" \
            -C "${PROJECT_ROOT}/config" postfix
    fi

    # Nginx configuration
    if [[ -d "${PROJECT_ROOT}/config/nginx" ]]; then
        log_info "  - Backing up Nginx configuration..."
        tar -czf "${BACKUP_DIR}/config/nginx_config.tar.gz" \
            -C "${PROJECT_ROOT}/config" nginx
    fi

    # Roundcube configuration
    if [[ -d "${PROJECT_ROOT}/config/roundcube" ]]; then
        log_info "  - Backing up Roundcube configuration..."
        tar -czf "${BACKUP_DIR}/config/roundcube_config.tar.gz" \
            -C "${PROJECT_ROOT}/config" roundcube
    fi

    # Rspamd configuration
    if [[ -d "${PROJECT_ROOT}/config/rspamd" ]]; then
        log_info "  - Backing up Rspamd configuration..."
        tar -czf "${BACKUP_DIR}/config/rspamd_config.tar.gz" \
            -C "${PROJECT_ROOT}/config" rspamd
    fi

    # ClamAV configuration
    if [[ -d "${PROJECT_ROOT}/config/clamav" ]]; then
        log_info "  - Backing up ClamAV configuration..."
        tar -czf "${BACKUP_DIR}/config/clamav_config.tar.gz" \
            -C "${PROJECT_ROOT}/config" clamav
    fi

    # Usermgmt application code (excluding venv, __pycache__)
    if [[ -d "${PROJECT_ROOT}/usermgmt" ]]; then
        log_info "  - Backing up Usermgmt application..."
        tar -czf "${BACKUP_DIR}/config/usermgmt_app.tar.gz" \
            -C "${PROJECT_ROOT}" \
            --exclude='usermgmt/venv' \
            --exclude='usermgmt/__pycache__' \
            --exclude='usermgmt/**/__pycache__' \
            --exclude='usermgmt/.pytest_cache' \
            --exclude='usermgmt/htmlcov' \
            usermgmt
    fi

    log_info "Configuration backup completed"
}

# Backup Docker configurations
backup_docker_configs() {
    log_info "Backing up Docker configurations..."

    # docker-compose.yml
    if [[ -f "${PROJECT_ROOT}/docker-compose.yml" ]]; then
        log_info "  - Backing up docker-compose.yml..."
        cp "${PROJECT_ROOT}/docker-compose.yml" \
            "${BACKUP_DIR}/docker/docker-compose.yml"
    fi

    # .env file
    if [[ -f "${PROJECT_ROOT}/.env" ]]; then
        log_info "  - Backing up .env file..."
        cp "${PROJECT_ROOT}/.env" \
            "${BACKUP_DIR}/docker/env"
    fi

    # Dockerfile(s)
    if [[ -f "${PROJECT_ROOT}/usermgmt/Dockerfile" ]]; then
        log_info "  - Backing up Usermgmt Dockerfile..."
        cp "${PROJECT_ROOT}/usermgmt/Dockerfile" \
            "${BACKUP_DIR}/docker/usermgmt_Dockerfile"
    fi

    log_info "Docker configuration backup completed"
}

# Backup logs (last 7 days only to save space)
backup_logs() {
    log_info "Backing up recent logs (last 7 days)..."

    if [[ -d "${PROJECT_ROOT}/logs" ]]; then
        # Find and backup logs from last 7 days
        find "${PROJECT_ROOT}/logs" -type f -mtime -7 -print0 | \
            tar -czf "${BACKUP_DIR}/logs/recent_logs.tar.gz" \
                --null -T -
        log_info "Logs backup completed"
    else
        log_warn "Logs directory not found, skipping"
    fi
}

# Backup mail data (optional, large volume)
backup_mail_data() {
    if [[ "${INCLUDE_MAIL_DATA}" == "true" ]]; then
        log_info "Backing up mail data (this may take a while)..."

        if [[ -d "${PROJECT_ROOT}/data/mail" ]]; then
            tar -czf "${BACKUP_DIR}/mail_data.tar.gz" \
                -C "${PROJECT_ROOT}/data" mail
            log_info "Mail data backup completed"
        else
            log_warn "Mail data directory not found, skipping"
        fi
    else
        log_info "Skipping mail data backup (use --include-mail-data to include)"
    fi
}

# Create backup manifest
create_manifest() {
    log_info "Creating backup manifest..."

    cat > "${BACKUP_DIR}/MANIFEST.txt" <<EOF
Mailserver Backup Manifest
==========================

Backup Date: $(date)
Backup Directory: ${BACKUP_DIR}
Hostname: $(hostname)
Include Mail Data: ${INCLUDE_MAIL_DATA}

Contents:
---------
$(find "${BACKUP_DIR}" -type f -exec ls -lh {} \; | awk '{print $9, "("$5")"}')

Docker Container Status:
-----------------------
$(docker compose -f "${PROJECT_ROOT}/docker-compose.yml" ps)

Disk Usage:
-----------
Total Backup Size: $(du -sh "${BACKUP_DIR}" | awk '{print $1}')

Checksum (SHA256):
------------------
$(find "${BACKUP_DIR}" -type f ! -name "MANIFEST.txt" -exec sha256sum {} \; | sort)
EOF

    log_info "Manifest created: ${BACKUP_DIR}/MANIFEST.txt"
}

# Cleanup old backups (keep last 7 days)
cleanup_old_backups() {
    log_info "Cleaning up backups older than 7 days..."

    if [[ -d "${BACKUP_ROOT}" ]]; then
        find "${BACKUP_ROOT}" -maxdepth 1 -type d -mtime +7 -exec rm -rf {} \;
        log_info "Cleanup completed"
    fi
}

# Main backup procedure
main() {
    log_info "========================================="
    log_info "Mailserver Backup Starting"
    log_info "========================================="
    log_info "Timestamp: ${TIMESTAMP}"
    log_info "Backup directory: ${BACKUP_DIR}"
    log_info ""

    create_backup_dir
    backup_databases
    backup_configs
    backup_docker_configs
    backup_logs
    backup_mail_data
    create_manifest
    cleanup_old_backups

    log_info ""
    log_info "========================================="
    log_info "Backup Completed Successfully"
    log_info "========================================="
    log_info "Backup location: ${BACKUP_DIR}"
    log_info "Total size: $(du -sh "${BACKUP_DIR}" | awk '{print $1}')"
    log_info ""
    log_info "To restore from this backup, see:"
    log_info "  docs/application/mailserver/usermgmt/ROLLBACK.md"
}

# Run main function
main "$@"
