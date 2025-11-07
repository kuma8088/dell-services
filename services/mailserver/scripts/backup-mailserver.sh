#!/bin/bash
#
# backup-mailserver.sh - Dell Mailserver Backup Script
# Version: 1.2
#
# Usage: ./backup-mailserver.sh [--daily|--weekly]
#
# Changelog:
# - v1.2 (2025-11-07): CRITICAL FIX - Added set +e/set -e around tar to prevent
#                      script termination on non-zero exit codes (set -e issue)
# - v1.1 (2025-11-07): Fixed tar error handling - now properly checks exit codes
#                      and excludes non-critical root-owned files (sasl_passwd*)
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/backup-config.sh"

if [[ ! -f "${CONFIG_FILE}" ]]; then
    echo "Configuration file not found: ${CONFIG_FILE}" >&2
    exit 1
fi

# shellcheck disable=SC1091
source "${CONFIG_FILE}"

BACKUP_TYPE="daily"
START_TS=$(date +%s)
BACKUP_DATE=$(date '+%Y-%m-%d')
WEEK_ID=$(date '+%Y-week-%U')
BACKUP_DIR=""
EXIT_CODE=0
SUMMARY_LOG=()
MYSQL_PASSWORD=""
MYSQL_USER_VALUE="${MYSQL_USER}"
BACKUP_MOUNTPOINT="$(dirname "${BACKUP_ROOT}")"

usage() {
    cat <<EOF
Usage: $0 [--daily|--weekly]

Options:
  --daily     Run daily backup (default)
  --weekly    Run weekly backup
  --help      Show this help
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --daily)
            BACKUP_TYPE="daily"
            shift
            ;;
        --weekly)
            BACKUP_TYPE="weekly"
            shift
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
done

log() {
    local level="$1"
    local message="$2"
    local component="${3:-MAIN}"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local entry="[${timestamp}] [${level}] [${component}] ${message}"

    printf '%s\n' "${entry}"

    if [[ -n "${LOG_FILE}" ]]; then
        printf '%s\n' "${entry}" >> "${LOG_FILE}"
    fi
    if [[ -n "${ERROR_LOG}" && ( "${level}" == "ERROR" || "${level}" == "CRITICAL" ) ]]; then
        printf '%s\n' "${entry}" >> "${ERROR_LOG}"
    fi
    if [[ "${level}" == "CRITICAL" ]] && command -v logger >/dev/null 2>&1; then
        logger -t "mailserver-backup" -p user.crit "${message}"
    fi
}

trim() {
    local var="$*"
    var="${var#"${var%%[![:space:]]*}"}"
    var="${var%"${var##*[![:space:]]}"}"
    printf '%s' "${var}"
}

is_true() {
    local val
    val="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
    [[ "${val}" == "true" || "${val}" == "1" || "${val}" == "yes" ]]
}

add_summary() {
    SUMMARY_LOG+=("$1")
}

retry_command() {
    local attempt=1
    local max_attempts="${MAX_RETRIES}"
    local delay="${RETRY_DELAY}"

    while (( attempt <= max_attempts )); do
        if "$@"; then
            return 0
        fi
        log "ERROR" "Attempt ${attempt}/${max_attempts} failed: $*" "RETRY"
        if (( attempt < max_attempts )); then
            log "INFO" "Retrying in ${delay}s..." "RETRY"
            sleep "${delay}"
            delay=$(( delay * 2 ))
        fi
        attempt=$(( attempt + 1 ))
    done

    log "CRITICAL" "Command failed after ${max_attempts} attempts: $*" "RETRY"
    return 1
}

cleanup_on_exit() {
    if [[ -f "${LOCK_FILE}" ]]; then
        rm -f "${LOCK_FILE}"
    fi
    if [[ -n "${TEMP_DIR:-}" && -d "${TEMP_DIR}" ]]; then
        rm -rf "${TEMP_DIR}"
    fi
}

trap cleanup_on_exit EXIT
trap 'log "ERROR" "Backup interrupted" "MAIN"; exit 130' INT TERM

ensure_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        log "CRITICAL" "Required command not found: $1" "INIT"
        return 1
    fi
}

read_mysql_credentials() {
    if [[ ! -f "${MYSQL_CONFIG_FILE}" ]]; then
        log "ERROR" "MySQL config not found: ${MYSQL_CONFIG_FILE}" "MYSQL"
        return 1
    fi

    local line key value
    while IFS='=' read -r key value; do
        key=$(trim "${key}")
        value=$(trim "${value}")

        [[ -z "${key}" ]] && continue
        [[ "${key}" =~ ^# ]] && continue

        case "${key}" in
            user)
                MYSQL_USER_VALUE="${value}"
                ;;
            password)
                MYSQL_PASSWORD="${value}"
                ;;
        esac
    done < "${MYSQL_CONFIG_FILE}"

    if [[ -z "${MYSQL_PASSWORD}" ]]; then
        log "CRITICAL" "MySQL password not found in ${MYSQL_CONFIG_FILE}" "MYSQL"
        return 1
    fi
}

initialize() {
    log "INFO" "Backup started (type: ${BACKUP_TYPE})" "INIT"

    if [[ "$(id -u)" -ne 0 && "$(whoami)" != "system-admin" ]]; then
        log "CRITICAL" "Run as root or system-admin" "INIT"
        return 1
    fi

    mkdir -p "$(dirname "${LOG_FILE}")" "$(dirname "${ERROR_LOG}")"
    touch "${LOG_FILE}" "${ERROR_LOG}"

    ensure_command rsync || return 1
    ensure_command tar || return 1
    ensure_command gzip || return 1
    ensure_command docker || return 1
    ensure_command sha256sum || return 1

    if [[ -f "${LOCK_FILE}" ]]; then
        log "ERROR" "Lock file exists (${LOCK_FILE}); another backup may be running" "INIT"
        return 1
    fi
    echo "$$" > "${LOCK_FILE}"

    mkdir -p "${BACKUP_ROOT}" "${DAILY_BACKUP_DIR}" "${WEEKLY_BACKUP_DIR}"

    if [[ ! -d "${BACKUP_MOUNTPOINT}" ]]; then
        log "CRITICAL" "Backup mount point missing: ${BACKUP_MOUNTPOINT}" "INIT"
        return 1
    fi

    if ! mountpoint -q "${BACKUP_MOUNTPOINT}"; then
        log "CRITICAL" "Backup HDD not mounted at ${BACKUP_MOUNTPOINT}" "INIT"
        return 1
    fi

    local disk_usage
    disk_usage=$(df -P "${BACKUP_MOUNTPOINT}" | awk 'NR==2 {gsub("%","",$5); print $5}')
    log "INFO" "Backup disk usage: ${disk_usage}%" "INIT"
    if (( disk_usage >= DISK_WARNING_THRESHOLD )); then
        log "WARNING" "Disk usage exceeded threshold (${disk_usage}% >= ${DISK_WARNING_THRESHOLD}%)" "INIT"
        send_disk_warning "${disk_usage}"
    fi

    if [[ "${BACKUP_TYPE}" == "daily" ]]; then
        BACKUP_DIR="${DAILY_BACKUP_DIR}/${BACKUP_DATE}"
    else
        BACKUP_DIR="${WEEKLY_BACKUP_DIR}/${WEEK_ID}"
    fi
    mkdir -p "${BACKUP_DIR}"/{mail,mysql,config,ssl,dkim}

    mkdir -p "${TEMP_DIR}"

    read_mysql_credentials
}

send_disk_warning() {
    local usage="$1"
    if ! is_true "${NOTIFICATION_ON_FAILURE}"; then
        return
    fi
    if ! command -v sendmail >/dev/null 2>&1; then
        log "WARNING" "sendmail not available; cannot send disk warning" "NOTIFY"
        return
    fi
    if [[ -z "${ADMIN_EMAIL}" ]]; then
        log "WARNING" "ADMIN_EMAIL not configured; skipping disk warning" "NOTIFY"
        return
    fi

    {
        printf "To: %s\n" "${ADMIN_EMAIL}"
        printf "Subject: [Mailserver Backup] Disk usage warning (%s%%)\n" "${usage}"
        printf "Content-Type: text/plain; charset=UTF-8\n\n"
        printf "Backup disk usage has reached %s%% (threshold %s%%).\n" "${usage}" "${DISK_WARNING_THRESHOLD}"
        printf "Please review /mnt/backup-hdd to ensure sufficient capacity.\n"
    } | sendmail -t
}

backup_mail() {
    log "INFO" "Starting mail backup" "MAIL"
    if [[ ! -d "${MAIL_DATA_DIR}" ]]; then
        log "ERROR" "Mail data directory missing: ${MAIL_DATA_DIR}" "MAIL"
        return 1
    fi

    local rsync_opts=(
        -a
        -v
        --delete
        --exclude='*.tmp'
        --exclude='*.lock'
    )

    if retry_command rsync "${rsync_opts[@]}" "${MAIL_DATA_DIR}/" "${BACKUP_DIR}/mail/"; then
        local size
        size=$(du -sh "${BACKUP_DIR}/mail" | awk '{print $1}')
        log "INFO" "Mail backup completed (${size})" "MAIL"
        add_summary "MAIL: success (${size})"
        return 0
    else
        log "ERROR" "Mail backup failed" "MAIL"
        add_summary "MAIL: failed"
        return 1
    fi
}

backup_mysql() {
    log "INFO" "Starting MySQL backup" "MYSQL"

    if ! docker ps --format '{{.Names}}' | grep -Fxq "${MYSQL_CONTAINER}"; then
        log "ERROR" "MySQL container not running: ${MYSQL_CONTAINER}" "MYSQL"
        add_summary "MYSQL: failed (container missing)"
        return 1
    fi

    local db
    local failures=0
    read -r -a MYSQL_DB_ARRAY <<< "${MYSQL_DATABASES}"

    for db in "${MYSQL_DB_ARRAY[@]}"; do
        local dest="${BACKUP_DIR}/mysql/${db}.sql.gz"
        log "INFO" "Backing up database: ${db}" "MYSQL"
        if docker exec -i "${MYSQL_CONTAINER}" env MYSQL_PWD="${MYSQL_PASSWORD}" mysqldump \
            -u "${MYSQL_USER_VALUE}" \
            --single-transaction \
            --routines \
            --triggers \
            --events \
            "${db}" | gzip > "${dest}"; then
            log "INFO" "Database backup complete: ${dest}" "MYSQL"
        else
            log "ERROR" "mysqldump failed for ${db}" "MYSQL"
            failures=$((failures + 1))
        fi
    done

    if (( failures > 0 )); then
        add_summary "MYSQL: failed (${failures} errors)"
        return 1
    fi

    local mysql_size
    mysql_size=$(du -sh "${BACKUP_DIR}/mysql" | awk '{print $1}')
    add_summary "MYSQL: success (${mysql_size})"
    return 0
}

archive_directory() {
    local source_dir="$1"
    local dest_file="$2"
    local component="$3"
    local tar_stderr
    local tar_exit_code

    if [[ ! -d "${source_dir}" ]]; then
        log "WARNING" "${component} source missing (${source_dir}); skipping" "${component}"
        return 0
    fi

    # Exclude root-owned files that are not critical for recovery
    # sasl_passwd* files are regenerated by Postfix container on startup
    # Temporarily disable errexit to capture tar exit code
    set +e
    tar_stderr=$(tar -czf "${dest_file}" \
        --exclude='postfix/sasl_passwd' \
        --exclude='postfix/sasl_passwd.db' \
        -C "${source_dir}" . 2>&1)
    tar_exit_code=$?
    set -e

    # Check tar exit code
    if [[ ${tar_exit_code} -eq 2 ]]; then
        # Fatal error (exit code 2)
        log "ERROR" "${component} archive failed: ${tar_stderr}" "${component}"
        return 1
    elif [[ ${tar_exit_code} -eq 1 ]]; then
        # Some files differ (exit code 1) - acceptable for running systems
        log "WARNING" "${component} archive completed with warnings: ${tar_stderr}" "${component}"
    fi

    # Verify archive was created
    if [[ ! -f "${dest_file}" ]]; then
        log "ERROR" "${component} archive file not created" "${component}"
        return 1
    fi

    return 0
}

backup_config() {
    log "INFO" "Archiving configuration files" "CONFIG"
    if archive_directory "${CONFIG_DIR}" "${BACKUP_DIR}/config/config.tar.gz" "CONFIG"; then
        add_summary "CONFIG: success"
        return 0
    fi
    add_summary "CONFIG: failed"
    return 1
}

backup_ssl() {
    log "INFO" "Archiving SSL data" "SSL"
    if archive_directory "${SSL_DIR}" "${BACKUP_DIR}/ssl/certbot.tar.gz" "SSL"; then
        add_summary "SSL: success"
        return 0
    fi
    add_summary "SSL: failed"
    return 1
}

backup_dkim() {
    log "INFO" "Archiving DKIM keys" "DKIM"
    if archive_directory "${DKIM_DIR}" "${BACKUP_DIR}/dkim/dkim.tar.gz" "DKIM"; then
        add_summary "DKIM: success"
        return 0
    fi
    add_summary "DKIM: failed"
    return 1
}

backup_env_and_compose() {
    log "INFO" "Copying docker-compose.yml and .env" "DOCKER"
    local status=0

    if [[ -f "${DOCKER_COMPOSE_FILE}" ]]; then
        cp "${DOCKER_COMPOSE_FILE}" "${BACKUP_DIR}/config/docker-compose.yml"
    else
        log "WARNING" "docker-compose file not found: ${DOCKER_COMPOSE_FILE}" "DOCKER"
        status=1
    fi

    if [[ -f "${ENV_FILE}" ]]; then
        cp "${ENV_FILE}" "${BACKUP_DIR}/config/env"
    else
        log "WARNING" ".env file not found: ${ENV_FILE}" "DOCKER"
        status=1
    fi

    if (( status == 0 )); then
        add_summary "DOCKER: success"
        return 0
    fi

    add_summary "DOCKER: partial"
    return 1
}

verify_backup() {
    log "INFO" "Verifying backup artifacts" "VERIFY"
    local checksum_file="${BACKUP_DIR}/checksums.sha256"

    if ! find "${BACKUP_DIR}" -type f >/dev/null 2>&1; then
        log "ERROR" "Backup directory empty: ${BACKUP_DIR}" "VERIFY"
        add_summary "VERIFY: failed (empty backup)"
        return 1
    fi

    (
        cd "${BACKUP_DIR}"
        find . -type f ! -name "checksums.sha256" -print0 | \
            while IFS= read -r -d '' file; do
                sha256sum "${file#./}"
            done > "${checksum_file}"
    )

    if (cd "${BACKUP_DIR}" && sha256sum -c checksums.sha256 >/dev/null); then
        log "INFO" "Checksum verification passed" "VERIFY"
        add_summary "VERIFY: success"
        return 0
    fi

    log "ERROR" "Checksum verification failed" "VERIFY"
    add_summary "VERIFY: failed"
    return 1
}

write_backup_log() {
    local end_ts
    end_ts=$(date +%s)
    local duration=$(( end_ts - START_TS ))
    local total_size="N/A"
    if [[ -d "${BACKUP_DIR}" ]]; then
        total_size=$(du -sh "${BACKUP_DIR}" | awk '{print $1}')
    fi

    local log_file="${BACKUP_DIR}/backup.log"
    {
        printf "Backup Type: %s\n" "${BACKUP_TYPE}"
        printf "Start Time: %s\n" "$(date -d "@${START_TS}" '+%Y-%m-%d %H:%M:%S')"
        printf "End Time: %s\n" "$(date -d "@${end_ts}" '+%Y-%m-%d %H:%M:%S')"
        printf "Duration: %s seconds\n" "${duration}"
        printf "Backup Directory: %s\n" "${BACKUP_DIR}"
        printf "Total Size: %s\n" "${total_size}"
        printf "\nStep Summary:\n"
        for entry in "${SUMMARY_LOG[@]}"; do
            printf "  - %s\n" "${entry}"
        done
    } > "${log_file}"
}

cleanup_old_backups() {
    log "INFO" "Cleaning up old backups" "CLEANUP"

    if [[ -d "${DAILY_BACKUP_DIR}" ]]; then
        find "${DAILY_BACKUP_DIR}" -mindepth 1 -maxdepth 1 -type d -mtime +"${DAILY_RETENTION_DAYS}" -print -exec rm -rf {} +
    fi
    local weekly_days=$(( WEEKLY_RETENTION_WEEKS * 7 ))
    if [[ -d "${WEEKLY_BACKUP_DIR}" ]]; then
        find "${WEEKLY_BACKUP_DIR}" -mindepth 1 -maxdepth 1 -type d -mtime +"${weekly_days}" -print -exec rm -rf {} +
    fi
}

update_latest_link() {
    if [[ "${BACKUP_TYPE}" == "daily" ]]; then
        ln -sfn "${BACKUP_DIR}" "${LATEST_LINK}"
    fi
}

send_notification() {
    local status="$1"

    if [[ "${status}" == "SUCCESS" ]]; then
        if ! is_true "${NOTIFICATION_ON_SUCCESS}"; then
            return
        fi
    elif [[ "${status}" == "FAILURE" ]]; then
        if ! is_true "${NOTIFICATION_ON_FAILURE}"; then
            return
        fi
    fi
    if [[ -z "${ADMIN_EMAIL}" ]]; then
        log "WARNING" "ADMIN_EMAIL not set; cannot send ${status} notification" "NOTIFY"
        return
    fi
    if ! command -v sendmail >/dev/null 2>&1; then
        log "WARNING" "sendmail not available; skipping notification" "NOTIFY"
        return
    fi

    local subject="[Mailserver Backup] ${status}"
    local body
    body=$(
        printf "Backup Type: %s\n" "${BACKUP_TYPE}"
        printf "Directory: %s\n" "${BACKUP_DIR}"
        printf "Status: %s\n" "${status}"
        printf "\nSummary:\n"
        for entry in "${SUMMARY_LOG[@]}"; do
            printf "  - %s\n" "${entry}"
        done
        printf "\nSee %s for details.\n" "${LOG_FILE}"
    )

    {
        printf "To: %s\n" "${ADMIN_EMAIL}"
        printf "Subject: %s\n" "${subject}"
        printf "Content-Type: text/plain; charset=UTF-8\n\n"
        printf "%s\n" "${body}"
    } | sendmail -t
}

run_step() {
    local label="$1"
    shift
    if "$@"; then
        return 0
    fi
    log "ERROR" "${label} failed" "MAIN"
    EXIT_CODE=1
    return 1
}

main() {
    if ! initialize; then
        log "CRITICAL" "Initialization failed" "INIT"
        EXIT_CODE=1
        return
    fi

    run_step "Mail backup" backup_mail
    run_step "MySQL backup" backup_mysql
    run_step "Config backup" backup_config
    run_step "SSL backup" backup_ssl
    run_step "DKIM backup" backup_dkim
    run_step "Compose/env backup" backup_env_and_compose
    run_step "Verification" verify_backup
    cleanup_old_backups
    update_latest_link
    write_backup_log

    local status="SUCCESS"
    if (( EXIT_CODE != 0 )); then
        status="FAILURE"
    fi
    send_notification "${status}"
    log "INFO" "Backup finished with status: ${status}" "MAIN"
    return "${EXIT_CODE}"
}

main "$@"
