#!/bin/bash
# scan-restored-data.sh - Phase 11-B Restored Data Malware Scan
#
# Purpose: Scan S3-restored data for malware before applying to system
# Usage: ./scan-restored-data.sh --source /path/to/restored/data
#
# Features:
#   - ClamAV antivirus scanning
#   - Pre-restore malware detection
#   - Block restore if malware detected
#   - Comprehensive logging
#
# Exit Codes:
#   0 - Clean (safe to restore)
#   1 - Malware detected or scan error (DO NOT restore)

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

SOURCE_DIR=""

# Parse command line options
while [[ $# -gt 0 ]]; do
    case "$1" in
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

# Validate --source option
if [ -z "$SOURCE_DIR" ]; then
    echo "ERROR: --source option is required"
    echo "Usage: $0 --source /path/to/restored/data"
    exit 1
fi

# Validate source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    log "ERROR: Source directory not found: ${SOURCE_DIR}"
    exit 1
fi

# Scan log
SCAN_LOG="${LOG_FILE%.log}-restore-scan.log"

# =====================================================
# Pre-flight Checks
# =====================================================

log "=========================================="
log "Phase 11-B: Restored Data Malware Scan"
log "Source: ${SOURCE_DIR}"
log "=========================================="

# Check ClamAV
if ! command -v clamscan &>/dev/null; then
    log "ERROR: ClamAV not installed"
    log "Please install ClamAV: sudo dnf install clamav clamd"
    exit 1
fi

log "ClamAV found: $(clamscan --version | head -n1)"

# Update virus database
log "Updating ClamAV virus database..."
if sudo freshclam 2>&1 | tee -a "$SCAN_LOG"; then
    log "Virus database updated successfully"
else
    log "WARNING: Virus database update failed (continuing with existing database)"
fi

# =====================================================
# Scan Restored Data
# =====================================================

log "Scanning restored data for malware..."
log "This may take several minutes depending on data size..."

# Calculate scan size
SCAN_SIZE=$(du -sh "$SOURCE_DIR" | awk '{print $1}')
log "Scan size: ${SCAN_SIZE}"

# Run ClamAV scan
if clamscan \
    --recursive \
    --infected \
    --log="${SCAN_LOG}" \
    --max-filesize=50M \
    --max-scansize=100M \
    "$SOURCE_DIR" 2>&1 | tee -a "$LOG_FILE"; then

    log "=========================================="
    log "Scan Result: CLEAN"
    log "No malware detected in restored data"
    log "Safe to proceed with restore"
    log "=========================================="

    exit 0
else
    SCAN_EXIT_CODE=$?

    if [ $SCAN_EXIT_CODE -eq 1 ]; then
        log "=========================================="
        log "CRITICAL: MALWARE DETECTED IN RESTORED DATA"
        log "=========================================="
        log "DO NOT proceed with restore!"
        log "Review scan log: ${SCAN_LOG}"
        log "=========================================="

        # Send email alert
        if [ -n "$ADMIN_EMAIL" ]; then
            ALERT_SUBJECT="[CRITICAL] Malware Detected in S3 Restored Data"
            ALERT_BODY="Malware scan detected threats in S3-restored backup data.

Source: ${SOURCE_DIR}
Scan Time: $(date)
Scan Log: ${SCAN_LOG}

RESTORE HAS BEEN BLOCKED FOR SECURITY REASONS.

Action required:
1. Review the scan log to identify infected files
2. Investigate backup integrity
3. Do NOT restore this backup
4. Attempt restore from an earlier clean backup

---
Phase 11-B S3 Backup System
"

            echo "$ALERT_BODY" | mail -s "$ALERT_SUBJECT" "$ADMIN_EMAIL" || {
                log "ERROR: Failed to send email alert to ${ADMIN_EMAIL}"
            }

            log "Email alert sent to ${ADMIN_EMAIL}"
        fi

        # Exit with error to block restore
        exit 1
    else
        log "ERROR: ClamAV scan failed with exit code ${SCAN_EXIT_CODE}"
        log "Unable to verify data safety. Aborting restore."
        exit 1
    fi
fi
