#!/bin/bash
# backup-to-s3.sh - Phase 11-B S3 Backup Upload
#
# Purpose: Upload local backup to AWS S3 with Object Lock COMPLIANCE mode
# Usage: ./backup-to-s3.sh [--date YYYY-MM-DD]
#
# Features:
#   - Upload daily local backup to S3
#   - Create and upload checksum file
#   - Verify S3 Object Lock configuration
#   - Lock file management for concurrent execution prevention
#   - Comprehensive logging
#
# Exit Codes:
#   0 - Success
#   1 - Error (local backup not found, AWS auth fail, S3 upload fail)

set -euo pipefail

# =====================================================
# Load Configuration
# =====================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load backup configuration
# shellcheck source=backup-config.sh
source "${SCRIPT_DIR}/backup-config.sh"

# Source preflight checks library
PREFLIGHT_LIB="${SCRIPT_DIR}/preflight-checks.sh"
if [[ -f "${PREFLIGHT_LIB}" ]]; then
    # shellcheck disable=SC1091
    source "${PREFLIGHT_LIB}"
fi

# =====================================================
# Parameters and Variables
# =====================================================

# Backup date (default: yesterday)
BACKUP_DATE="${1:-$(date -d "yesterday" '+%Y-%m-%d')}"

# Parse command line options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --date)
            BACKUP_DATE="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Local backup directory
LOCAL_BACKUP_DIR="${DAILY_BACKUP_DIR}/${BACKUP_DATE}"

# S3 configuration overrides
: "${S3_PREFIX:=}"
: "${S3_TIER:=daily}"
: "${S3_INCLUDE_PATTERNS:=mail/* mysql/* config/* dkim/* ssl/* checksums.sha256 backup.log}"

# S3 destination
if [[ -n "${S3_PREFIX}" ]]; then
    S3_DESTINATION="${S3_BUCKET}/${S3_PREFIX}/${S3_TIER}/${BACKUP_DATE}"
else
    S3_DESTINATION="${S3_BUCKET}/${S3_TIER}/${BACKUP_DATE}"
fi

# Checksum file
CHECKSUM_FILE="${LOCAL_BACKUP_DIR}/checksums.sha256"

# =====================================================
# Pre-flight Checks
# =====================================================

log "=========================================="
log "Phase 11-B: S3 Backup Upload Started"
log "Backup Date: ${BACKUP_DATE}"
log "=========================================="

# Run pre-flight checks
if command -v run_preflight_checks >/dev/null 2>&1; then
    if ! run_preflight_checks \
        --disk-space 10 \
        --env-vars "S3_BUCKET,AWS_DEFAULT_REGION,DAILY_BACKUP_DIR" \
        --files "${LOCAL_BACKUP_DIR}/checksums.sha256" \
        2>&1 | tee -a "$LOG_FILE"; then
        log "ERROR: Pre-flight checks failed"
        exit 1
    fi
else
    log "INFO: Preflight checks library not available, using legacy checks"
fi

# Check lock file
if ! check_lock_file; then
    log "ERROR: Another backup process is running"
    exit 1
fi

# Create lock file
create_lock_file

# Cleanup function
cleanup() {
    local exit_code=$?
    remove_lock_file

    if [ $exit_code -eq 0 ]; then
        log "S3 backup completed successfully"
    else
        log "ERROR: S3 backup failed with exit code ${exit_code}"
    fi

    log "=========================================="
    exit $exit_code
}

trap cleanup EXIT INT TERM

# Verify local backup exists
if [ ! -d "$LOCAL_BACKUP_DIR" ]; then
    log "ERROR: Local backup not found: ${LOCAL_BACKUP_DIR}"
    exit 1
fi

log "Local backup found: ${LOCAL_BACKUP_DIR}"

# Verify AWS authentication
if ! aws sts get-caller-identity &>/dev/null; then
    log "ERROR: AWS authentication failed"
    log "Please check AWS_PROFILE (${AWS_PROFILE}) and AWS credentials"
    exit 1
fi

log "AWS authentication successful"
log "Account ID: ${AWS_ACCOUNT_ID}"
log "Region: ${AWS_DEFAULT_REGION}"

# Verify S3 bucket exists
if ! aws s3 ls "s3://${S3_BUCKET}/" &>/dev/null; then
    log "ERROR: S3 bucket not found or not accessible: ${S3_BUCKET}"
    exit 1
fi

log "S3 bucket accessible: ${S3_BUCKET}"

# =====================================================
# Create Checksum File
# =====================================================

log "Creating checksum file..."

(
    cd "$LOCAL_BACKUP_DIR"

    # Generate checksums for all files
    find . -type f ! -name "checksums.sha256" ! -name "backup.log" -exec sha256sum {} \; > checksums.sha256

    log "Checksum file created: $(wc -l < checksums.sha256) files"
)

# =====================================================
# Upload to S3
# =====================================================

log "Uploading to S3: s3://${S3_DESTINATION}/"

# Upload with aws s3 sync
INCLUDE_ARGS=()
for pattern in ${S3_INCLUDE_PATTERNS}; do
    INCLUDE_ARGS+=(--include "${pattern}")
done

if aws s3 sync \
    "$LOCAL_BACKUP_DIR/" \
    "s3://${S3_DESTINATION}/" \
    --storage-class STANDARD \
    --no-progress \
    --exclude "*" \
    "${INCLUDE_ARGS[@]}" \
    2>&1 | tee -a "$LOG_FILE"; then

    log "S3 upload completed successfully"
else
    log "ERROR: S3 upload failed"
    exit 1
fi

# =====================================================
# Verify Object Lock (if enabled)
# =====================================================

log "Verifying Object Lock configuration..."

# Check if Object Lock is enabled on the bucket
OBJECT_LOCK_ENABLED=$(aws s3api get-object-lock-configuration \
    --bucket "${S3_BUCKET}" \
    --query 'ObjectLockConfiguration.ObjectLockEnabled' \
    --output text 2>/dev/null || echo "")

if [ "$OBJECT_LOCK_ENABLED" = "Enabled" ]; then
    log "Object Lock is enabled on bucket ${S3_BUCKET}"
    log "Backup is protected from deletion for retention period"
else
    log "WARNING: Object Lock is not enabled on bucket ${S3_BUCKET}"
    log "Backup is not protected from accidental deletion"
fi

# =====================================================
# Upload Summary
# =====================================================

# Calculate upload size
UPLOAD_SIZE=$(du -sh "$LOCAL_BACKUP_DIR" | awk '{print $1}')

log "=========================================="
log "Upload Summary:"
log "  Date: ${BACKUP_DATE}"
log "  Size: ${UPLOAD_SIZE}"
log "  Destination: s3://${S3_DESTINATION}/"
log "  Object Lock: ${OBJECT_LOCK_ENABLED:-Disabled}"
log "=========================================="

# =====================================================
# Cost Monitoring Alert (Optional)
# =====================================================

# Calculate estimated storage cost (rough estimate)
# S3 Standard: $0.025/GB/month in ap-northeast-1
# Use printf to avoid scientific notation (bc cannot parse 1.2e-05 style strings)
UPLOAD_SIZE_GB=$(du -sb "$LOCAL_BACKUP_DIR" | awk '{printf "%.10f", $1/1024/1024/1024}')
if command -v bc >/dev/null 2>&1; then
    ESTIMATED_COST_RAW=$(echo "$UPLOAD_SIZE_GB * 0.025" | bc -l 2>/dev/null | tr -d '\n')
    if [[ -n "$ESTIMATED_COST_RAW" ]]; then
        ESTIMATED_COST=$(printf "%.6f" "$ESTIMATED_COST_RAW")
    else
        ESTIMATED_COST="N/A"
    fi
else
    ESTIMATED_COST="N/A"
fi

log "Estimated monthly storage cost: \$${ESTIMATED_COST}"

# Alert if cost exceeds threshold (100 JPY ≈ $0.70)
if [ "$ESTIMATED_COST" != "N/A" ]; then
    if (( $(echo "$ESTIMATED_COST > 0.70" | bc -l) )); then
        log "WARNING: Estimated cost exceeds threshold"

        if [ -n "$ADMIN_EMAIL" ]; then
            echo "S3 backup cost alert: \$${ESTIMATED_COST}/month" | \
                mail -s "[WARNING] S3 Backup Cost Alert" "$ADMIN_EMAIL" || true
        fi
    fi
fi

log "S3 backup upload completed successfully"

exit 0
