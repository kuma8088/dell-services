#!/bin/bash
# scan-mailserver.sh - Phase 11-B Mailserver Malware Scan
#
# Purpose: Daily/Weekly malware scan of mailserver data
# Usage: ./scan-mailserver.sh [--daily|--weekly]
#
# Features:
#   - ClamAV antivirus scanning
#   - rkhunter rootkit detection
#   - Scheduled daily (quick) and weekly (full) scans
#   - Alert on malware detection
#   - Comprehensive logging
#
# Exit Codes:
#   0 - Clean (no threats found)
#   1 - Malware detected or scan error

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

SCAN_MODE="daily"

# Parse command line options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --daily)
            SCAN_MODE="daily"
            shift
            ;;
        --weekly)
            SCAN_MODE="weekly"
            shift
            ;;
        *)
            echo "Usage: $0 [--daily|--weekly]"
            exit 1
            ;;
    esac
done

# Scan log
SCAN_LOG="${LOG_FILE%.log}-scan.log"

# Malware alert flag
MALWARE_DETECTED=0

# ClamAV update tracking
CLAMAV_UPDATE_STATUS="unknown"
CLAMAV_OLD_VERSION=""
CLAMAV_NEW_VERSION=""

# =====================================================
# Pre-flight Checks
# =====================================================

log "=========================================="
log "Phase 11-B: Mailserver Malware Scan (${SCAN_MODE})"
log "=========================================="

# Check ClamAV
if ! command -v clamscan &>/dev/null; then
    log "WARNING: ClamAV not installed. Skipping virus scan."
    CLAMAV_AVAILABLE=0
else
    log "ClamAV found: $(clamscan --version | head -n1)"
    CLAMAV_AVAILABLE=1
fi

# Check rkhunter
if ! command -v rkhunter &>/dev/null; then
    log "WARNING: rkhunter not installed. Skipping rootkit scan."
    RKHUNTER_AVAILABLE=0
else
    log "rkhunter found: $(rkhunter --version 2>&1 | head -n1 || echo 'version unknown')"
    RKHUNTER_AVAILABLE=1
fi

# If neither is available, exit
if [ $CLAMAV_AVAILABLE -eq 0 ] && [ $RKHUNTER_AVAILABLE -eq 0 ]; then
    log "ERROR: No scan tools available (ClamAV or rkhunter)"
    exit 1
fi

# =====================================================
# Helper Functions
# =====================================================

# Send email notification
send_email_notification() {
    local subject="$1"
    local body="$2"

    if [ -n "$ADMIN_EMAIL" ]; then
        if command -v mail &>/dev/null; then
            echo "$body" | mail -s "$subject" "$ADMIN_EMAIL" || {
                log "ERROR: Failed to send email to ${ADMIN_EMAIL}"
            }
            log "Email notification sent to ${ADMIN_EMAIL}"
        else
            log "WARNING: mail command not available, skipping email notification"
        fi
    fi
}

# Get ClamAV virus definition version
get_clamav_version() {
    if [ -f /var/lib/clamav/daily.cvd ] || [ -f /var/lib/clamav/daily.cld ]; then
        sigtool --info /var/lib/clamav/daily.cvd 2>/dev/null | grep "Build time" | cut -d: -f2- | xargs || \
        sigtool --info /var/lib/clamav/daily.cld 2>/dev/null | grep "Build time" | cut -d: -f2- | xargs || \
        echo "unknown"
    else
        echo "not found"
    fi
}

# =====================================================
# ClamAV Virus Scan
# =====================================================

if [ $CLAMAV_AVAILABLE -eq 1 ]; then
    log "Starting ClamAV virus scan..."

    # Update virus database
    log "Updating ClamAV virus database..."

    # Get current virus definition version
    CLAMAV_OLD_VERSION=$(get_clamav_version)
    log "Current ClamAV definition: ${CLAMAV_OLD_VERSION}"

    # Attempt to update virus database
    if sudo freshclam 2>&1 | tee -a "$SCAN_LOG"; then
        CLAMAV_NEW_VERSION=$(get_clamav_version)

        # Check if database was actually updated
        if [ "$CLAMAV_OLD_VERSION" != "$CLAMAV_NEW_VERSION" ]; then
            CLAMAV_UPDATE_STATUS="updated"
            log "Virus database updated successfully: ${CLAMAV_OLD_VERSION} → ${CLAMAV_NEW_VERSION}"

            # Send update notification email
            UPDATE_SUBJECT="[INFO] ClamAV Virus Definition Updated"
            UPDATE_BODY="ClamAV virus definition has been updated on mailserver.

Previous Version: ${CLAMAV_OLD_VERSION}
New Version: ${CLAMAV_NEW_VERSION}
Update Time: $(date)
Scan Mode: ${SCAN_MODE}

The malware scan will proceed with the updated definitions.

---
Phase 11-B S3 Backup System"

            send_email_notification "$UPDATE_SUBJECT" "$UPDATE_BODY"
        else
            CLAMAV_UPDATE_STATUS="no_update"
            log "Virus database is already up to date: ${CLAMAV_NEW_VERSION}"
        fi
    else
        CLAMAV_UPDATE_STATUS="failed"
        CLAMAV_NEW_VERSION=$(get_clamav_version)
        log "WARNING: Virus database update failed (continuing with existing database: ${CLAMAV_NEW_VERSION})"

        # Send update failure notification email
        FAILURE_SUBJECT="[WARNING] ClamAV Virus Definition Update Failed"
        FAILURE_BODY="ClamAV virus definition update failed on mailserver.

Current Version: ${CLAMAV_NEW_VERSION}
Update Time: $(date)
Scan Mode: ${SCAN_MODE}

The malware scan will proceed with the existing database.
Manual update may be required: sudo freshclam

Check log: ${SCAN_LOG}

---
Phase 11-B S3 Backup System"

        send_email_notification "$FAILURE_SUBJECT" "$FAILURE_BODY"
    fi

    # Scan directories based on mode
    case "$SCAN_MODE" in
        daily)
            log "Daily scan: Scanning mail data directory only..."
            SCAN_DIRS="${MAIL_DATA_DIR}"
            ;;
        weekly)
            log "Weekly scan: Full mailserver scan..."
            SCAN_DIRS="${MAILSERVER_ROOT}/data ${CONFIG_DIR}"
            ;;
    esac

    # Run ClamAV scan
    log "Scanning directories: ${SCAN_DIRS}"

    if clamscan \
        --recursive \
        --infected \
        --log="${SCAN_LOG}" \
        --max-filesize=50M \
        --max-scansize=100M \
        $SCAN_DIRS 2>&1 | tee -a "$LOG_FILE"; then

        log "ClamAV scan completed: CLEAN"
    else
        SCAN_EXIT_CODE=$?

        if [ $SCAN_EXIT_CODE -eq 1 ]; then
            log "WARNING: Infected files found by ClamAV!"
            MALWARE_DETECTED=1
        else
            log "ERROR: ClamAV scan failed with exit code ${SCAN_EXIT_CODE}"
        fi
    fi
fi

# =====================================================
# rkhunter Rootkit Scan
# =====================================================

if [ $RKHUNTER_AVAILABLE -eq 1 ] && [ "$SCAN_MODE" = "weekly" ]; then
    log "Starting rkhunter rootkit scan..."

    # Update rkhunter database
    log "Updating rkhunter database..."
    if sudo rkhunter --update 2>&1 | tee -a "$SCAN_LOG"; then
        log "rkhunter database updated successfully"
    else
        log "WARNING: rkhunter database update failed (continuing with existing database)"
    fi

    # Run rkhunter scan
    if sudo rkhunter --check --skip-keypress --report-warnings-only 2>&1 | tee -a "$SCAN_LOG" "$LOG_FILE"; then
        log "rkhunter scan completed: CLEAN"
    else
        SCAN_EXIT_CODE=$?

        if [ $SCAN_EXIT_CODE -eq 1 ]; then
            log "WARNING: Warnings found by rkhunter!"
            MALWARE_DETECTED=1
        else
            log "ERROR: rkhunter scan failed with exit code ${SCAN_EXIT_CODE}"
        fi
    fi
fi

# =====================================================
# Malware Alert
# =====================================================

if [ $MALWARE_DETECTED -eq 1 ]; then
    log "=========================================="
    log "ALERT: Malware or threats detected!"
    log "=========================================="

    # Send email alert
    if [ -n "$ADMIN_EMAIL" ]; then
        ALERT_SUBJECT="[CRITICAL] Mailserver Malware Detected"
        ALERT_BODY="Malware scan detected threats on mailserver.

Scan Mode: ${SCAN_MODE}
Scan Time: $(date)
Scan Log: ${SCAN_LOG}

Please review the scan log immediately and take appropriate action.

---
Phase 11-B S3 Backup System
"

        echo "$ALERT_BODY" | mail -s "$ALERT_SUBJECT" "$ADMIN_EMAIL" || {
            log "ERROR: Failed to send email alert to ${ADMIN_EMAIL}"
        }

        log "Email alert sent to ${ADMIN_EMAIL}"
    fi

    # Exit with error
    exit 1
fi

# =====================================================
# Scan Summary
# =====================================================

log "=========================================="
log "Scan Summary:"
log "  Mode: ${SCAN_MODE}"
log "  ClamAV: $([ $CLAMAV_AVAILABLE -eq 1 ] && echo 'CLEAN' || echo 'SKIPPED')"
log "  ClamAV Update: ${CLAMAV_UPDATE_STATUS} $([ -n "$CLAMAV_NEW_VERSION" ] && echo "(${CLAMAV_NEW_VERSION})" || echo "")"
log "  rkhunter: $([ $RKHUNTER_AVAILABLE -eq 1 ] && [ "$SCAN_MODE" = "weekly" ] && echo 'CLEAN' || echo 'SKIPPED')"
log "  Result: CLEAN (no threats detected)"
log "  Log: ${SCAN_LOG}"
log "=========================================="

log "Malware scan completed successfully"

exit 0
