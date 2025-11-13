#!/bin/bash
set -euo pipefail

BACKUP_DATE_DEFAULT=$(date -d "yesterday" '+%Y-%m-%d')
BACKUP_DATE="${BACKUP_DATE_DEFAULT}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --date)
      if [[ -z "${2:-}" ]]; then
        echo "ERROR: --date requires YYYY-MM-DD" >&2
        exit 1
      fi
      BACKUP_DATE="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: $(basename "$0") [--date YYYY-MM-DD]"
      exit 0
      ;;
    *)
      BACKUP_DATE="$1"
      shift
      ;;
  esac
done

PROJECT_ROOT="/opt/onprem-infra-system/project-root-infra"
RENTAL_ROOT="/mnt/backup-hdd/rental"
LOG_FILE="/home/system-admin/.rental-backup.log"
ERROR_LOG="/home/system-admin/.rental-backup-error.log"

log() {
  local message="$1"
  local ts
  ts=$(date '+%Y-%m-%d %H:%M:%S')
  local entry="[${ts}] [S3] ${message}"
  echo "${entry}"
  printf '%s\n' "${entry}" >> "${LOG_FILE}"
}

upload_mail() {
  log "Uploading mail backup for ${BACKUP_DATE}"
  (
    export BACKUP_ROOT="${RENTAL_ROOT}/mail"
    export DAILY_BACKUP_DIR="${RENTAL_ROOT}/mail/daily"
    export LOG_FILE
    export ERROR_LOG
    export LOCK_FILE="/tmp/rental-mail-s3.lock"
    export S3_PREFIX="mail"
    export S3_INCLUDE_PATTERNS="mail/* mysql/* config/* dkim/* ssl/* checksums.sha256 backup.log"
    cd "${PROJECT_ROOT}/services/mailserver"
    ./scripts/backup-to-s3.sh --date "${BACKUP_DATE}"
  )
  log "Mail backup upload completed"
}

upload_blog() {
  log "Uploading blog backup for ${BACKUP_DATE}"
  (
    export BACKUP_ROOT="${RENTAL_ROOT}/blog"
    export DAILY_BACKUP_DIR="${RENTAL_ROOT}/blog/daily"
    export LOG_FILE
    export ERROR_LOG
    export LOCK_FILE="/tmp/rental-blog-s3.lock"
    export S3_PREFIX="blog"
    export S3_INCLUDE_PATTERNS="sites/* mysql/* config/* checksums.sha256 backup.log"
    cd "${PROJECT_ROOT}/services/mailserver"
    ./scripts/backup-to-s3.sh --date "${BACKUP_DATE}"
  )
  log "Blog backup upload completed"
}

upload_mail
upload_blog
