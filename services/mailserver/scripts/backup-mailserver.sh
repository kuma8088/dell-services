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

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/shared/common.sh"

# Configuration
SCRIPT_DIR="${MAILSERVER_SCRIPTS_DIR}"
PROJECT_ROOT="${MAILSERVER_PROJECT_ROOT}"
BACKUP_ROOT="${PROJECT_ROOT}/backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"

# Include mail data in backup (large, optional)
INCLUDE_MAIL_DATA=false
if [[ "${1:-}" == "--include-mail-data" ]]; then
    INCLUDE_MAIL_DATA=true
fi

# Create backup directory
create_backup_dir() {
    mailserver_log_info "Creating backup directory: ${BACKUP_DIR}"
    mkdir -p "${BACKUP_DIR}"/{database,config,docker,logs}
}

# Backup MariaDB databases
backup_databases() {
    mailserver_log_info "Backing up MariaDB databases..."

    # Load DB password from .env
    if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
        mailserver_log_error ".env file not found at ${PROJECT_ROOT}/.env"
        return 1
    fi

    # shellcheck disable=SC1091
    source "${PROJECT_ROOT}/.env"

    # Backup usermgmt database
    mailserver_log_info "  - Backing up mailserver_usermgmt database..."
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
    mailserver_log_info "  - Backing up ${MYSQL_DATABASE} database..."
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
    mailserver_log_info "  - Compressing database backups..."
    gzip "${BACKUP_DIR}/database/"*.sql

    mailserver_log_info "Database backup completed"
}

# Backup configuration files
backup_configs() {
    mailserver_log_info "Backing up configuration files..."

    # Dovecot configuration
    if [[ -d "${PROJECT_ROOT}/config/dovecot" ]]; then
        mailserver_log_info "  - Backing up Dovecot configuration..."
        tar -czf "${BACKUP_DIR}/config/dovecot_config.tar.gz" \
            -C "${PROJECT_ROOT}/config" dovecot
    fi

    # Postfix configuration
    if [[ -d "${PROJECT_ROOT}/config/postfix" ]]; then
        mailserver_log_info "  - Backing up Postfix configuration..."
        tar -czf "${BACKUP_DIR}/config/postfix_config.tar.gz" \
            -C "${PROJECT_ROOT}/config" postfix
    fi

    # Nginx configuration
    if [[ -d "${PROJECT_ROOT}/config/nginx" ]]; then
        mailserver_log_info "  - Backing up Nginx configuration..."
        tar -czf "${BACKUP_DIR}/config/nginx_config.tar.gz" \
            -C "${PROJECT_ROOT}/config" nginx
    fi

    # Roundcube configuration
    if [[ -d "${PROJECT_ROOT}/config/roundcube" ]]; then
        mailserver_log_info "  - Backing up Roundcube configuration..."
        tar -czf "${BACKUP_DIR}/config/roundcube_config.tar.gz" \
            -C "${PROJECT_ROOT}/config" roundcube
    fi

    # Rspamd configuration
    if [[ -d "${PROJECT_ROOT}/config/rspamd" ]]; then
        mailserver_log_info "  - Backing up Rspamd configuration..."
        tar -czf "${BACKUP_DIR}/config/rspamd_config.tar.gz" \
            -C "${PROJECT_ROOT}/config" rspamd
    fi

    # ClamAV configuration
    if [[ -d "${PROJECT_ROOT}/config/clamav" ]]; then
        mailserver_log_info "  - Backing up ClamAV configuration..."
        tar -czf "${BACKUP_DIR}/config/clamav_config.tar.gz" \
            -C "${PROJECT_ROOT}/config" clamav
    fi

    # Usermgmt application code (excluding venv, __pycache__)
    if [[ -d "${PROJECT_ROOT}/usermgmt" ]]; then
        mailserver_log_info "  - Backing up Usermgmt application..."
        tar -czf "${BACKUP_DIR}/config/usermgmt_app.tar.gz" \
            -C "${PROJECT_ROOT}" \
            --exclude='usermgmt/venv' \
            --exclude='usermgmt/__pycache__' \
            --exclude='usermgmt/**/__pycache__' \
            --exclude='usermgmt/.pytest_cache' \
            --exclude='usermgmt/htmlcov' \
            usermgmt
    fi

    mailserver_log_info "Configuration backup completed"
}

# Backup Docker configurations
backup_docker_configs() {
    mailserver_log_info "Backing up Docker configurations..."

    # docker-compose.yml
    if [[ -f "${PROJECT_ROOT}/docker-compose.yml" ]]; then
        mailserver_log_info "  - Backing up docker-compose.yml..."
        cp "${PROJECT_ROOT}/docker-compose.yml" \
            "${BACKUP_DIR}/docker/docker-compose.yml"
    fi

    # .env file
    if [[ -f "${PROJECT_ROOT}/.env" ]]; then
        mailserver_log_info "  - Backing up .env file..."
        cp "${PROJECT_ROOT}/.env" \
            "${BACKUP_DIR}/docker/env"
    fi

    # Dockerfile(s)
    if [[ -f "${PROJECT_ROOT}/usermgmt/Dockerfile" ]]; then
        mailserver_log_info "  - Backing up Usermgmt Dockerfile..."
        cp "${PROJECT_ROOT}/usermgmt/Dockerfile" \
            "${BACKUP_DIR}/docker/usermgmt_Dockerfile"
    fi

    mailserver_log_info "Docker configuration backup completed"
}

# Backup logs (last 7 days only to save space)
backup_logs() {
    mailserver_log_info "Backing up recent logs (last 7 days)..."

    if [[ -d "${PROJECT_ROOT}/logs" ]]; then
        # Find and backup logs from last 7 days
        find "${PROJECT_ROOT}/logs" -type f -mtime -7 -print0 | \
            tar -czf "${BACKUP_DIR}/logs/recent_logs.tar.gz" \
                --null -T -
        mailserver_log_info "Logs backup completed"
    else
        mailserver_log_warn "Logs directory not found, skipping"
    fi
}

# Backup mail data (optional, large volume)
backup_mail_data() {
    if [[ "${INCLUDE_MAIL_DATA}" == "true" ]]; then
        mailserver_log_info "Backing up mail data (this may take a while)..."

        if [[ -d "${PROJECT_ROOT}/data/mail" ]]; then
            tar -czf "${BACKUP_DIR}/mail_data.tar.gz" \
                -C "${PROJECT_ROOT}/data" mail
            mailserver_log_info "Mail data backup completed"
        else
            mailserver_log_warn "Mail data directory not found, skipping"
        fi
    else
        mailserver_log_info "Skipping mail data backup (use --include-mail-data to include)"
    fi
}

# Create backup manifest
create_manifest() {
    mailserver_log_info "Creating backup manifest..."

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

    mailserver_log_info "Manifest created: ${BACKUP_DIR}/MANIFEST.txt"
}

# Cleanup old backups (keep last 7 days)
cleanup_old_backups() {
    mailserver_log_info "Cleaning up backups older than 7 days..."

    if [[ -d "${BACKUP_ROOT}" ]]; then
        find "${BACKUP_ROOT}" -maxdepth 1 -type d -mtime +7 -exec rm -rf {} \;
        mailserver_log_info "Cleanup completed"
    fi
}

# Main backup procedure
main() {
    mailserver_log_info "========================================="
    mailserver_log_info "Mailserver Backup Starting"
    mailserver_log_info "========================================="
    mailserver_log_info "Timestamp: ${TIMESTAMP}"
    mailserver_log_info "Backup directory: ${BACKUP_DIR}"
    mailserver_log_info ""

    create_backup_dir
    backup_databases
    backup_configs
    backup_docker_configs
    backup_logs
    backup_mail_data
    create_manifest
    cleanup_old_backups

    mailserver_log_info ""
    mailserver_log_info "========================================="
    mailserver_log_info "Backup Completed Successfully"
    mailserver_log_info "========================================="
    mailserver_log_info "Backup location: ${BACKUP_DIR}"
    mailserver_log_info "Total size: $(du -sh "${BACKUP_DIR}" | awk '{print $1}')"
    mailserver_log_info ""
    mailserver_log_info "To restore from this backup, see:"
    mailserver_log_info "  docs/application/mailserver/usermgmt/ROLLBACK.md"
}

# Run main function
main "$@"
