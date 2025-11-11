#!/bin/bash
#
# preflight-checks.sh - Common Pre-flight Checks Library
# Version: 1.0
# Created: 2025-11-11
#
# Purpose: Provides common validation functions for mailserver scripts
# Usage: source ./preflight-checks.sh
#

# Preflight check: Disk space
# Args: $1 = required space in GB (default: 50)
# Returns: 0 if OK, 1 if insufficient
check_disk_space() {
    local required_gb="${1:-50}"
    local required_kb=$((required_gb * 1024 * 1024))
    local mountpoint="${BACKUP_MOUNTPOINT:-/mnt/backup-hdd}"

    if [[ ! -d "${mountpoint}" ]]; then
        echo "ERROR: Backup mountpoint does not exist: ${mountpoint}" >&2
        return 1
    fi

    local available_kb
    available_kb=$(df "${mountpoint}" 2>/dev/null | awk 'NR==2 {print $4}')

    if [[ -z "${available_kb}" ]]; then
        echo "ERROR: Could not determine available disk space for ${mountpoint}" >&2
        return 1
    fi

    if [[ "${available_kb}" -lt "${required_kb}" ]]; then
        local available_gb=$((available_kb / 1024 / 1024))
        echo "ERROR: Insufficient disk space on ${mountpoint}" >&2
        echo "  Required: ${required_gb}GB, Available: ${available_gb}GB" >&2
        return 1
    fi

    return 0
}

# Preflight check: Docker daemon
# Returns: 0 if OK, 1 if not responding
check_docker_daemon() {
    if ! docker ps > /dev/null 2>&1; then
        echo "ERROR: Docker daemon not responding" >&2
        echo "  Try: systemctl status docker" >&2
        return 1
    fi
    return 0
}

# Preflight check: Required containers running
# Args: $@ = list of required container names
# Returns: 0 if all OK, 1 if any missing
check_required_containers() {
    local missing=()
    local container

    for container in "$@"; do
        if ! docker ps --filter "name=${container}" --filter "status=running" --format "{{.Names}}" | grep -q "^${container}$"; then
            missing+=("${container}")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "ERROR: Required containers not running:" >&2
        printf '  - %s\n' "${missing[@]}" >&2
        echo "  Try: docker compose ps" >&2
        return 1
    fi

    return 0
}

# Preflight check: Required environment variables
# Args: $@ = list of required variable names
# Returns: 0 if all set, 1 if any missing
check_required_env_vars() {
    local missing=()
    local var

    for var in "$@"; do
        if [[ -z "${!var:-}" ]]; then
            missing+=("${var}")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "ERROR: Required environment variables not set:" >&2
        printf '  - %s\n' "${missing[@]}" >&2
        return 1
    fi

    return 0
}

# Preflight check: Required files exist
# Args: $@ = list of required file paths
# Returns: 0 if all exist, 1 if any missing
check_required_files() {
    local missing=()
    local file

    for file in "$@"; do
        if [[ ! -f "${file}" ]]; then
            missing+=("${file}")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "ERROR: Required files not found:" >&2
        printf '  - %s\n' "${missing[@]}" >&2
        return 1
    fi

    return 0
}

# Run all preflight checks
# Args: --disk-space <GB> --containers <name1,name2> --env-vars <VAR1,VAR2> --files <path1,path2>
# Returns: 0 if all pass, 1 if any fail
run_preflight_checks() {
    local disk_space_gb=50
    local containers=()
    local env_vars=()
    local files=()
    local failed=0

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --disk-space)
                disk_space_gb="$2"
                shift 2
                ;;
            --containers)
                IFS=',' read -ra containers <<< "$2"
                shift 2
                ;;
            --env-vars)
                IFS=',' read -ra env_vars <<< "$2"
                shift 2
                ;;
            --files)
                IFS=',' read -ra files <<< "$2"
                shift 2
                ;;
            *)
                echo "ERROR: Unknown preflight check option: $1" >&2
                return 1
                ;;
        esac
    done

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running pre-flight checks..."

    # Check disk space
    if ! check_disk_space "${disk_space_gb}"; then
        failed=1
    else
        echo "  ✓ Disk space OK (${disk_space_gb}GB+ available)"
    fi

    # Check Docker daemon
    if ! check_docker_daemon; then
        failed=1
    else
        echo "  ✓ Docker daemon OK"
    fi

    # Check required containers
    if [[ ${#containers[@]} -gt 0 ]]; then
        if ! check_required_containers "${containers[@]}"; then
            failed=1
        else
            echo "  ✓ Required containers OK"
        fi
    fi

    # Check required environment variables
    if [[ ${#env_vars[@]} -gt 0 ]]; then
        if ! check_required_env_vars "${env_vars[@]}"; then
            failed=1
        else
            echo "  ✓ Required environment variables OK"
        fi
    fi

    # Check required files
    if [[ ${#files[@]} -gt 0 ]]; then
        if ! check_required_files "${files[@]}"; then
            failed=1
        else
            echo "  ✓ Required files OK"
        fi
    fi

    if [[ ${failed} -eq 1 ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pre-flight checks FAILED" >&2
        return 1
    fi

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pre-flight checks PASSED"
    return 0
}
