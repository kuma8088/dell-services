#!/bin/bash
#
# restore-mailserver.sh - Mailserver Restore Script
#
# Usage:
#   ./restore-mailserver.sh --from /mnt/backup-hdd/mailserver/latest [--component all|mail|mysql|config|ssl|dkim]
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

BACKUP_SOURCE=""
COMPONENT="all"
RESTORE_TEMP_DIR="/tmp/mailserver-restore-$$"
MYSQL_PASSWORD=""
MYSQL_USER_VALUE="${MYSQL_USER}"
DRY_RUN=0
RESTORE_LOG="$HOME/.mailserver-restore.log"

usage() {
    cat <<EOF
Usage: $0 --from BACKUP_PATH [OPTIONS]

Required:
  --from PATH          Backup directory path to restore from

Options:
  --component NAME     Component to restore (all, mail, mysql, config, ssl, dkim)
  --dry-run            Show what would be restored without actually restoring
  -h, --help           Show this help message

Examples:
  $0 --from /mnt/backup-hdd/mailserver/latest
  $0 --from /mnt/backup-hdd/mailserver/daily/2025-11-07 --component mysql
  $0 --from /mnt/backup-hdd/mailserver/latest --dry-run
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --from)
            BACKUP_SOURCE="$2"
            shift 2
            ;;
        --component)
            COMPONENT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
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

if [[ -z "${BACKUP_SOURCE}" ]]; then
    echo "--from BACKUP_PATH is required" >&2
    usage
    exit 1
fi

COMPONENT="$(printf '%s' "${COMPONENT}" | tr '[:upper:]' '[:lower:]')"

log() {
    local level="$1"
    local message="$2"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local entry="[${timestamp}] [${level}] ${message}"

    printf '%s\n' "${entry}"

    if [[ -n "${RESTORE_LOG}" ]]; then
        printf '%s\n' "${entry}" >> "${RESTORE_LOG}"
    fi
}

trim() {
    local var="$*"
    var="${var#"${var%%[![:space:]]*}"}"
    var="${var%"${var##*[![:space:]]}"}"
    printf '%s' "${var}"
}

read_mysql_credentials() {
    if [[ ! -f "${MYSQL_CONFIG_FILE}" ]]; then
        log "ERROR" "MySQL config not found: ${MYSQL_CONFIG_FILE}"
        return 1
    fi

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
        log "ERROR" "MySQL password not found in ${MYSQL_CONFIG_FILE}"
        return 1
    fi
}

cleanup() {
    if [[ -d "${RESTORE_TEMP_DIR}" ]]; then
        rm -rf "${RESTORE_TEMP_DIR}"
    fi
}

trap cleanup EXIT

require_root() {
    if [[ "$(id -u)" -ne 0 && "$(whoami)" != "system-admin" ]]; then
        log "ERROR" "Run as root or system-admin"
        exit 1
    fi
}

validate_backup() {
    if [[ ! -d "${BACKUP_SOURCE}" ]]; then
        log "ERROR" "Backup directory not found: ${BACKUP_SOURCE}"
        exit 1
    fi

    if [[ -f "${BACKUP_SOURCE}/checksums.sha256" ]]; then
        log "INFO" "Validating backup checksums..."
        if ! (cd "${BACKUP_SOURCE}" && sha256sum -c checksums.sha256); then
            log "WARNING" "Checksum validation failed; proceed with caution"
        fi
    else
        log "WARNING" "Checksum file missing; skipping integrity validation"
    fi
}

backup_existing_dir() {
    local target="$1"
    local label="$2"

    if [[ -d "${target}" ]]; then
        local backup_path="${target}.bak.$(date +%Y%m%d_%H%M%S)"
        log "INFO" "Backing up existing ${label} to ${backup_path}"
        mv "${target}" "${backup_path}"
    fi
    mkdir -p "${target}"
}

restore_mail() {
    local source_mail="${BACKUP_SOURCE}/mail"
    if [[ ! -d "${source_mail}" ]]; then
        log "ERROR" "Mail backup not found in ${source_mail}"
        return 1
    fi

    if [[ ${DRY_RUN} -eq 1 ]]; then
        log "INFO" "[DRY-RUN] Would backup existing mail data to ${MAIL_DATA_DIR}.bak.*"
        log "INFO" "[DRY-RUN] Would restore mail data from ${source_mail}/ to ${MAIL_DATA_DIR}/"
        log "INFO" "[DRY-RUN] Estimated size: $(du -sh "${source_mail}" | cut -f1)"
        return 0
    fi

    backup_existing_dir "${MAIL_DATA_DIR}" "mail data"
    log "INFO" "Restoring mail data with rsync..."
    rsync -a "${source_mail}/" "${MAIL_DATA_DIR}/"
}

restore_mysql() {
    local source_mysql="${BACKUP_SOURCE}/mysql"
    if [[ ! -d "${source_mysql}" ]]; then
        log "ERROR" "MySQL backup not found in ${source_mysql}"
        return 1
    fi

    if ! docker ps --format '{{.Names}}' | grep -Fxq "${MYSQL_CONTAINER}"; then
        log "ERROR" "MySQL container not running: ${MYSQL_CONTAINER}"
        return 1
    fi

    read_mysql_credentials

    shopt -s nullglob
    local files=("${source_mysql}"/*.sql.gz)
    if [[ ${#files[@]} -eq 0 ]]; then
        shopt -u nullglob
        log "ERROR" "No .sql.gz files in ${source_mysql}"
        return 1
    fi

    if [[ ${DRY_RUN} -eq 1 ]]; then
        log "INFO" "[DRY-RUN] Would restore ${#files[@]} database(s):"
        for dump in "${files[@]}"; do
            local filename
            filename="$(basename "${dump}")"
            local db="${filename%.sql.gz}"
            local size
            size=$(du -sh "${dump}" | cut -f1)
            log "INFO" "[DRY-RUN]   - ${db} (${size})"
        done
        shopt -u nullglob
        return 0
    fi

    local status=0
    for dump in "${files[@]}"; do
        local filename
        filename="$(basename "${dump}")"
        local db="${filename%.sql.gz}"
        log "INFO" "Restoring database ${db} from ${filename}"
        docker exec -i "${MYSQL_CONTAINER}" env MYSQL_PWD="${MYSQL_PASSWORD}" mysql -u "${MYSQL_USER_VALUE}" -e "DROP DATABASE IF EXISTS \`${db}\`; CREATE DATABASE \`${db}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        if ! gunzip -c "${dump}" | docker exec -i "${MYSQL_CONTAINER}" env MYSQL_PWD="${MYSQL_PASSWORD}" mysql -u "${MYSQL_USER_VALUE}" "${db}"; then
            log "ERROR" "Restore failed for database ${db}"
            status=1
            break
        fi
    done
    shopt -u nullglob
    return "${status}"
}

restore_tarball() {
    local tarball="$1"
    local destination="$2"
    local label="$3"

    if [[ ! -f "${tarball}" ]]; then
        log "ERROR" "${label} tarball not found: ${tarball}"
        return 1
    fi

    if [[ ${DRY_RUN} -eq 1 ]]; then
        local size
        size=$(du -sh "${tarball}" | cut -f1)
        log "INFO" "[DRY-RUN] Would backup existing ${label} to ${destination}.bak.*"
        log "INFO" "[DRY-RUN] Would extract ${label} tarball (${size}) to ${destination}/"
        return 0
    fi

    backup_existing_dir "${destination}" "${label}"
    mkdir -p "${destination}"
    tar -xzf "${tarball}" -C "${destination}"
}

restore_config() {
    restore_tarball "${BACKUP_SOURCE}/config/config.tar.gz" "${CONFIG_DIR}" "configuration" || return 1
    
    if [[ ${DRY_RUN} -eq 1 ]]; then
        if [[ -f "${BACKUP_SOURCE}/config/docker-compose.yml" ]]; then
            log "INFO" "[DRY-RUN] Would copy docker-compose.yml to ${MAILSERVER_ROOT}/"
        fi
        if [[ -f "${BACKUP_SOURCE}/config/env" ]]; then
            log "INFO" "[DRY-RUN] Would copy .env to ${MAILSERVER_ROOT}/"
        fi
        return 0
    fi
    
    if [[ -f "${BACKUP_SOURCE}/config/docker-compose.yml" ]]; then
        cp "${BACKUP_SOURCE}/config/docker-compose.yml" "${MAILSERVER_ROOT}/docker-compose.yml"
    fi
    if [[ -f "${BACKUP_SOURCE}/config/env" ]]; then
        cp "${BACKUP_SOURCE}/config/env" "${MAILSERVER_ROOT}/.env"
    fi
}

restore_ssl() {
    restore_tarball "${BACKUP_SOURCE}/ssl/certbot.tar.gz" "${MAILSERVER_ROOT}/data/certbot" "SSL" || return 1
}

restore_dkim() {
    restore_tarball "${BACKUP_SOURCE}/dkim/dkim.tar.gz" "${DKIM_DIR}" "DKIM" || return 1
}

restore_components() {
    case "${COMPONENT}" in
        all)
            restore_mail
            restore_mysql
            restore_config
            restore_ssl
            restore_dkim
            ;;
        mail)
            restore_mail
            ;;
        mysql)
            restore_mysql
            ;;
        config)
            restore_config
            ;;
        ssl)
            restore_ssl
            ;;
        dkim)
            restore_dkim
            ;;
        *)
            log "ERROR" "Unknown component: ${COMPONENT}"
            return 1
            ;;
    esac
}

ensure_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        log "ERROR" "Required command not found: $1"
        exit 1
    fi
}

main() {
    require_root
    ensure_command rsync
    ensure_command tar
    ensure_command docker
    ensure_command gunzip
    ensure_command sha256sum
    mkdir -p "${RESTORE_TEMP_DIR}"
    validate_backup
    restore_components
    log "INFO" "Restore completed successfully"
}

main
