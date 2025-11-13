#!/bin/bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: backup_rental.sh [--daily|--weekly]

Options:
  --daily    Run daily backup (default)
  --weekly   Run weekly backup
USAGE
}

BACKUP_TYPE="daily"
if [[ $# -gt 0 ]]; then
  case "$1" in
    --daily|daily)
      BACKUP_TYPE="daily"
      ;;
    --weekly|weekly)
      BACKUP_TYPE="weekly"
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
fi

PROJECT_ROOT="/opt/onprem-infra-system/project-root-infra"
RENTAL_ROOT="/mnt/backup-hdd/rental"
MAIL_ROOT="${RENTAL_ROOT}/mail"
BLOG_ROOT="${RENTAL_ROOT}/blog"
LOG_FILE="/home/system-admin/.rental-backup.log"
ERROR_LOG="/home/system-admin/.rental-backup-error.log"
BLOG_SITES_ROOT="/mnt/backup-hdd/blog/sites"
BLOG_ENV_FILE="${PROJECT_ROOT}/services/blog/.env"
BLOG_DB_CONTAINER="blog-mariadb"

BACKUP_DATE=$(date '+%Y-%m-%d')
WEEKLY_ID=$(date '+%Y-week-%U')
DATE_LABEL="${BACKUP_DATE}"
if [[ "${BACKUP_TYPE}" == "weekly" ]]; then
  DATE_LABEL="${WEEKLY_ID}"
fi

mkdir -p "${MAIL_ROOT}"/daily "${MAIL_ROOT}"/weekly
mkdir -p "${BLOG_ROOT}"/daily "${BLOG_ROOT}"/weekly

log() {
  local level="$1"; shift
  local component="$1"; shift
  local message="$*"
  local ts
  ts=$(date '+%Y-%m-%d %H:%M:%S')
  local entry="[${ts}] [${level}] [${component}] ${message}"
  echo "${entry}"
  printf '%s\n' "${entry}" >> "${LOG_FILE}"
  if [[ "${level}" == "ERROR" || "${level}" == "CRITICAL" ]]; then
    printf '%s\n' "${entry}" >> "${ERROR_LOG}"
  fi
}

load_blog_env() {
  if [[ -f "${BLOG_ENV_FILE}" ]]; then
    # shellcheck disable=SC1090
    source "${BLOG_ENV_FILE}"
    if [[ -z "${MYSQL_ROOT_PASSWORD:-}" ]]; then
      log ERROR BLOG "MYSQL_ROOT_PASSWORD not set in ${BLOG_ENV_FILE}"
      return 1
    fi
  else
    log ERROR BLOG "Blog .env not found: ${BLOG_ENV_FILE}"
    return 1
  fi
}

backup_mail() {
  log INFO MAIL "Starting mail backup (${BACKUP_TYPE})"
  (
    export BACKUP_ROOT="${MAIL_ROOT}"
    export DAILY_BACKUP_DIR="${MAIL_ROOT}/daily"
    export WEEKLY_BACKUP_DIR="${MAIL_ROOT}/weekly"
    export LATEST_LINK="${MAIL_ROOT}/latest"
    export LOG_FILE
    export ERROR_LOG
    export LOCK_FILE="/tmp/rental-mail-backup.lock"
    cd "${PROJECT_ROOT}/services/mailserver"
    if [[ "${BACKUP_TYPE}" == "weekly" ]]; then
      ./scripts/backup-mailserver.sh --weekly
    else
      ./scripts/backup-mailserver.sh --daily
    fi
  )
  log INFO MAIL "Mail backup completed"
}

backup_blog() {
  log INFO BLOG "Starting blog backup (${BACKUP_TYPE})"

  local target_dir sites_dir mysql_dir config_dir
  if [[ "${BACKUP_TYPE}" == "weekly" ]]; then
    target_dir="${BLOG_ROOT}/weekly/${DATE_LABEL}"
  else
    target_dir="${BLOG_ROOT}/daily/${DATE_LABEL}"
  fi
  sites_dir="${target_dir}/sites"
  mysql_dir="${target_dir}/mysql"
  config_dir="${target_dir}/config"

  mkdir -p "${sites_dir}" "${mysql_dir}" "${config_dir}"

  if [[ ! -d "${BLOG_SITES_ROOT}" ]]; then
    log ERROR BLOG "Blog sites directory missing: ${BLOG_SITES_ROOT}"
    return 1
  fi

  log INFO BLOG "Rsync WordPress sites"
  rsync -a --delete "${BLOG_SITES_ROOT}/" "${sites_dir}/"

  log INFO BLOG "Dumping MariaDB"
  load_blog_env || return 1
  docker exec -e MYSQL_PWD="${MYSQL_ROOT_PASSWORD}" "${BLOG_DB_CONTAINER}" \
    mysqldump -uroot --all-databases --single-transaction --quick --routines --events \
    | gzip > "${mysql_dir}/all-databases.sql.gz"

  log INFO BLOG "Archiving configuration"
  tar -czf "${config_dir}/blog-config.tar.gz" \
    -C "${PROJECT_ROOT}/services/blog" \
    docker-compose.yml .env config || {
      log ERROR BLOG "Failed to archive blog config"
      return 1
    }

  log INFO BLOG "Generating checksums"
  (cd "${target_dir}" && find . -type f ! -name 'checksums.sha256' -print0 | sort -z | xargs -0 sha256sum) > "${target_dir}/checksums.sha256"

  log INFO BLOG "Blog backup completed"
}

backup_mail
backup_blog

log INFO RENTAL "Rental backup finished (${BACKUP_TYPE})"
