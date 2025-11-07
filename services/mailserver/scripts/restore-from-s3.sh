#!/bin/bash
# restore-from-s3.sh - Phase 11-B S3 Backup Restore
#
# Purpose: Restore backup data from AWS S3
# Usage: ./restore-from-s3.sh [--date YYYY-MM-DD] [--component mail|mysql|config|all]
#
# Features:
#   - Restore latest or specific date backup from S3
#   - Checksum verification
#   - Component-specific restore (mail, mysql, config, or all)
#   - Malware scan before restore
#   - Comprehensive logging
#
# Exit Codes:
#   0 - Success
#   1 - Error (S3 download fail, checksum fail, malware detected)

set -euo pipefail

# =====================================================
# Load Configuration
# =====================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load backup configuration
# shellcheck source=backup-config.sh
source "${SCRIPT_DIR}/backup-config.sh"

# =====================================================
# Parameters and Variables
# =====================================================

# Default: restore latest backup
BACKUP_DATE=""
RESTORE_COMPONENT="all"

# Parse command line options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --date)
            BACKUP_DATE="$2"
            shift 2
            ;;
        --component)
            RESTORE_COMPONENT="$2"
            shift 2
            ;;
        *)
            echo "Usage: $0 [--date YYYY-MM-DD] [--component mail|mysql|config|all]"
            exit 1
            ;;
    esac
done

# Restore directory
RESTORE_DIR="${BACKUP_ROOT}/restore-$(date '+%Y%m%d%H%M%S')"

# =====================================================
# Pre-flight Checks
# =====================================================

log "=========================================="
log "Phase 11-B: S3 Backup Restore Started"
log "=========================================="

# Check lock file
if ! check_lock_file; then
    log "ERROR: Another restore process is running"
    exit 1
fi

# Create lock file
create_lock_file

# Cleanup function
cleanup() {
    local exit_code=$?
    remove_lock_file

    if [ $exit_code -eq 0 ]; then
        log "S3 restore completed successfully"
    else
        log "ERROR: S3 restore failed with exit code ${exit_code}"
    fi

    log "=========================================="
    exit $exit_code
}

trap cleanup EXIT INT TERM

# Verify AWS authentication
if ! aws sts get-caller-identity &>/dev/null; then
    log "ERROR: AWS authentication failed"
    exit 1
fi

log "AWS authentication successful"

# Verify S3 bucket exists
if ! aws s3 ls "s3://${S3_BUCKET}/" &>/dev/null; then
    log "ERROR: S3 bucket not found: ${S3_BUCKET}"
    exit 1
fi

log "S3 bucket accessible: ${S3_BUCKET}"

# =====================================================
# Determine Backup Date
# =====================================================

if [ -z "$BACKUP_DATE" ]; then
    log "Finding latest backup..."

    # Get latest backup date from S3
    BACKUP_DATE=$(aws s3 ls "s3://${S3_BUCKET}/daily/" | \
        awk '{print $2}' | \
        sed 's#/##g' | \
        sort -r | \
        head -n 1)

    if [ -z "$BACKUP_DATE" ]; then
        log "ERROR: No backups found in S3"
        exit 1
    fi

    log "Latest backup found: ${BACKUP_DATE}"
else
    log "Using specified date: ${BACKUP_DATE}"

    # Verify backup exists
    if ! aws s3 ls "s3://${S3_BUCKET}/daily/${BACKUP_DATE}/" &>/dev/null; then
        log "ERROR: Backup not found for date: ${BACKUP_DATE}"
        exit 1
    fi
fi

# S3 source path
S3_SOURCE="${S3_BUCKET}/daily/${BACKUP_DATE}"

# =====================================================
# Download from S3
# =====================================================

log "Downloading from S3: s3://${S3_SOURCE}/"

mkdir -p "$RESTORE_DIR"

# Download based on component selection
case "$RESTORE_COMPONENT" in
    mail)
        log "Downloading mail data only..."
        aws s3 sync "s3://${S3_SOURCE}/mail/" "${RESTORE_DIR}/mail/" --no-progress
        ;;
    mysql)
        log "Downloading MySQL data only..."
        aws s3 sync "s3://${S3_SOURCE}/mysql/" "${RESTORE_DIR}/mysql/" --no-progress
        ;;
    config)
        log "Downloading config data only..."
        aws s3 sync "s3://${S3_SOURCE}/config/" "${RESTORE_DIR}/config/" --no-progress
        aws s3 sync "s3://${S3_SOURCE}/dkim/" "${RESTORE_DIR}/dkim/" --no-progress
        aws s3 sync "s3://${S3_SOURCE}/ssl/" "${RESTORE_DIR}/ssl/" --no-progress
        ;;
    all)
        log "Downloading all components..."
        aws s3 sync "s3://${S3_SOURCE}/" "${RESTORE_DIR}/" --no-progress
        ;;
    *)
        log "ERROR: Invalid component: ${RESTORE_COMPONENT}"
        log "Valid components: mail, mysql, config, all"
        exit 1
        ;;
esac

log "S3 download completed"

# =====================================================
# Verify Checksum
# =====================================================

if [ -f "${RESTORE_DIR}/checksums.sha256" ]; then
    log "Verifying checksums..."

    (
        cd "$RESTORE_DIR"

        # Verify checksums
        if sha256sum -c checksums.sha256 2>&1 | tee -a "$LOG_FILE"; then
            log "Checksum verification: PASSED"
        else
            log "ERROR: Checksum verification FAILED"
            log "Data integrity compromised. Aborting restore."
            exit 1
        fi
    )
else
    log "WARNING: Checksum file not found. Skipping verification."
fi

# =====================================================
# Malware Scan
# =====================================================

log "Scanning restored data for malware..."

if [ -x "${SCRIPT_DIR}/scan-restored-data.sh" ]; then
    if "${SCRIPT_DIR}/scan-restored-data.sh" --source "$RESTORE_DIR"; then
        log "Malware scan: CLEAN"
    else
        log "ERROR: Malware detected in restored data"
        log "Aborting restore for security reasons"
        exit 1
    fi
else
    log "WARNING: scan-restored-data.sh not found. Skipping malware scan."
fi

# =====================================================
# Restore to System
# =====================================================

log "Restoring data to system..."

# Stop services before restore
log "Stopping mailserver services..."
(cd "${MAILSERVER_ROOT}" && docker compose stop) || true

case "$RESTORE_COMPONENT" in
    mail|all)
        log "Restoring mail data..."
        if [ -d "${RESTORE_DIR}/mail" ]; then
            rsync -av --delete "${RESTORE_DIR}/mail/" "${MAIL_DATA_DIR}/" | tee -a "$LOG_FILE"
            log "Mail data restored"
        fi
        ;& # fall through
esac

case "$RESTORE_COMPONENT" in
    mysql|all)
        log "Restoring MySQL data..."
        if [ -d "${RESTORE_DIR}/mysql" ]; then
            # Start MySQL container for import
            (cd "${MAILSERVER_ROOT}" && docker compose up -d mariadb) || true
            sleep 30

            # Import SQL dumps
            for sql_gz in "${RESTORE_DIR}"/mysql/*.sql.gz; do
                if [ -f "$sql_gz" ]; then
                    db_name=$(basename "${sql_gz}" .sql.gz)
                    log "Importing database: ${db_name}"

                    gunzip -c "${sql_gz}" | docker exec -i "${MYSQL_CONTAINER}" \
                        mysql -u "${MYSQL_USER}" 2>&1 | tee -a "$LOG_FILE"

                    log "Database ${db_name} restored"
                fi
            done
        fi
        ;& # fall through
esac

case "$RESTORE_COMPONENT" in
    config|all)
        log "Restoring configuration..."

        # Config files
        if [ -d "${RESTORE_DIR}/config" ]; then
            rsync -av "${RESTORE_DIR}/config/" "${CONFIG_DIR}/" | tee -a "$LOG_FILE"
            log "Config restored"
        fi

        # DKIM keys
        if [ -d "${RESTORE_DIR}/dkim" ]; then
            rsync -av "${RESTORE_DIR}/dkim/" "${DKIM_DIR}/" | tee -a "$LOG_FILE"
            log "DKIM keys restored"
        fi

        # SSL certificates
        if [ -d "${RESTORE_DIR}/ssl" ]; then
            rsync -av "${RESTORE_DIR}/ssl/" "${SSL_DIR}/" | tee -a "$LOG_FILE"
            log "SSL certificates restored"
        fi
        ;;
esac

# Restart services
log "Starting mailserver services..."
(cd "${MAILSERVER_ROOT}" && docker compose up -d) || true

# =====================================================
# Restore Summary
# =====================================================

RESTORE_SIZE=$(du -sh "$RESTORE_DIR" | awk '{print $1}')

log "=========================================="
log "Restore Summary:"
log "  Date: ${BACKUP_DATE}"
log "  Component: ${RESTORE_COMPONENT}"
log "  Size: ${RESTORE_SIZE}"
log "  Location: ${RESTORE_DIR}"
log "=========================================="

log "S3 restore completed successfully"
log "Please verify mailserver functionality"

exit 0
