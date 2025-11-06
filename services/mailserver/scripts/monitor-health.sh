#!/bin/bash
#
# Mailserver Health Monitoring Script
# Phase 9: Production Deployment Preparation
#
# Purpose: Continuous health monitoring of mailserver services
# - Container status checks
# - Healthcheck validation
# - Port availability
# - Log error detection
# - Resource usage monitoring
#
# Usage: ./monitor-health.sh [--alert-email your@email.com]
#

set -euo pipefail

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/shared/common.sh"

# Configuration
SCRIPT_DIR="${MAILSERVER_SCRIPTS_DIR}"
PROJECT_ROOT="${MAILSERVER_PROJECT_ROOT}"
LOG_FILE="${PROJECT_ROOT}/logs/health-monitor.log"
ALERT_EMAIL="${1:-}"

# Health check thresholds
CPU_THRESHOLD=80  # Percentage
MEM_THRESHOLD=80  # Percentage
DISK_THRESHOLD=85 # Percentage

# Colors for output
RED="${MAILSERVER_COLOR_RED}"
GREEN="${MAILSERVER_COLOR_GREEN}"
YELLOW="${MAILSERVER_COLOR_YELLOW}"
BLUE="${MAILSERVER_COLOR_BLUE}"
NC="${MAILSERVER_COLOR_RESET}"

# Status tracking
CRITICAL_COUNT=0
WARNING_COUNT=0
ISSUES=()

# Logging functions
log_info() {
    local msg="[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo -e "${GREEN}${msg}${NC}"
    echo "${msg}" >> "${LOG_FILE}"
}

log_warn() {
    local msg="[WARN] $(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo -e "${YELLOW}${msg}${NC}"
    echo "${msg}" >> "${LOG_FILE}"
    WARNING_COUNT=$((WARNING_COUNT + 1))
    ISSUES+=("⚠️  ${1}")
}

log_error() {
    local msg="[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo -e "${RED}${msg}${NC}"
    echo "${msg}" >> "${LOG_FILE}"
    CRITICAL_COUNT=$((CRITICAL_COUNT + 1))
    ISSUES+=("🚨 ${1}")
}

log_section() {
    mailserver_log_section "$1"
}

# Initialize log directory
mkdir -p "$(dirname "${LOG_FILE}")"

# Check container status
check_container_status() {
    log_section "Container Status Check"

    local services=(mariadb postfix dovecot roundcube usermgmt nginx rspamd clamav)

    for service in "${services[@]}"; do
        local container="mailserver-${service}"

        if docker inspect "${container}" &> /dev/null; then
            local status=$(docker inspect --format='{{.State.Status}}' "${container}")

            if [[ "${status}" == "running" ]]; then
                log_info "✓ ${container}: ${status}"
            else
                log_error "${container}: NOT running (status: ${status})"
            fi

            # Check restart count
            local restarts=$(docker inspect --format='{{.RestartCount}}' "${container}")
            if [[ ${restarts} -gt 5 ]]; then
                log_warn "${container}: High restart count (${restarts})"
            fi
        else
            log_error "${container}: Container not found"
        fi
    done
}

# Check healthcheck status
check_healthcheck_status() {
    log_section "Healthcheck Status"

    local services=(mariadb postfix dovecot roundcube usermgmt nginx rspamd clamav)

    for service in "${services[@]}"; do
        local container="mailserver-${service}"

        if docker inspect "${container}" &> /dev/null; then
            local health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "${container}")

            case "${health}" in
                healthy)
                    log_info "✓ ${container}: healthy"
                    ;;
                unhealthy)
                    log_error "${container}: UNHEALTHY"
                    # Get failing log
                    local faillog=$(docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' "${container}" | tail -n 5)
                    log_error "   Last healthcheck output: ${faillog}"
                    ;;
                starting)
                    log_warn "${container}: Starting (healthcheck pending)"
                    ;;
                no-healthcheck)
                    log_info "  ${container}: No healthcheck defined"
                    ;;
                *)
                    log_warn "${container}: Unknown health status (${health})"
                    ;;
            esac
        fi
    done
}

# Check service ports
check_service_ports() {
    log_section "Service Port Availability"

    local ports=(
        "587:SMTP Submission"
        "993:IMAPS"
        "995:POP3S"
        "2525:LMTP"
        "80:HTTP"
        "443:HTTPS"
    )

    for port_desc in "${ports[@]}"; do
        local port="${port_desc%%:*}"
        local desc="${port_desc##*:}"

        if nc -z localhost "${port}" 2>/dev/null; then
            log_info "✓ Port ${port} (${desc}): Listening"
        else
            log_error "Port ${port} (${desc}): NOT listening"
        fi
    done
}

# Check disk usage
check_disk_usage() {
    log_section "Disk Usage"

    # Check mail data volume
    local mail_usage=$(df -h "${PROJECT_ROOT}/data/mail" 2>/dev/null | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ -n "${mail_usage}" ]]; then
        if [[ ${mail_usage} -ge ${DISK_THRESHOLD} ]]; then
            log_error "Mail data disk usage: ${mail_usage}% (threshold: ${DISK_THRESHOLD}%)"
        elif [[ ${mail_usage} -ge 70 ]]; then
            log_warn "Mail data disk usage: ${mail_usage}%"
        else
            log_info "✓ Mail data disk usage: ${mail_usage}%"
        fi
    fi

    # Check database volume
    local db_usage=$(df -h "${PROJECT_ROOT}/data/db" 2>/dev/null | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ -n "${db_usage}" ]]; then
        if [[ ${db_usage} -ge ${DISK_THRESHOLD} ]]; then
            log_error "Database disk usage: ${db_usage}% (threshold: ${DISK_THRESHOLD}%)"
        elif [[ ${db_usage} -ge 70 ]]; then
            log_warn "Database disk usage: ${db_usage}%"
        else
            log_info "✓ Database disk usage: ${db_usage}%"
        fi
    fi
}

# Check container resource usage
check_container_resources() {
    log_section "Container Resource Usage"

    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemPerc}}\t{{.MemUsage}}" | \
        grep "mailserver-" | while read -r line; do
        local container=$(echo "${line}" | awk '{print $1}')
        local cpu=$(echo "${line}" | awk '{print $2}' | sed 's/%//')
        local mem=$(echo "${line}" | awk '{print $3}' | sed 's/%//')

        # Check CPU usage
        if (( $(echo "${cpu} > ${CPU_THRESHOLD}" | bc -l 2>/dev/null || echo 0) )); then
            log_error "${container}: High CPU usage (${cpu}%)"
        elif (( $(echo "${cpu} > 60" | bc -l 2>/dev/null || echo 0) )); then
            log_warn "${container}: Elevated CPU usage (${cpu}%)"
        fi

        # Check memory usage
        if (( $(echo "${mem} > ${MEM_THRESHOLD}" | bc -l 2>/dev/null || echo 0) )); then
            log_error "${container}: High memory usage (${mem}%)"
        elif (( $(echo "${mem} > 60" | bc -l 2>/dev/null || echo 0) )); then
            log_warn "${container}: Elevated memory usage (${mem}%)"
        fi
    done || true
}

# Check recent error logs
check_error_logs() {
    log_section "Recent Error Logs (last 5 minutes)"

    local services=(postfix dovecot nginx usermgmt)

    for service in "${services[@]}"; do
        local log_dir="${PROJECT_ROOT}/logs/${service}"

        if [[ -d "${log_dir}" ]]; then
            # Find recent errors
            local errors=$(find "${log_dir}" -type f -mmin -5 -exec grep -i "error\|fatal\|critical" {} \; 2>/dev/null | wc -l)

            if [[ ${errors} -gt 10 ]]; then
                log_warn "${service}: ${errors} errors found in last 5 minutes"
            elif [[ ${errors} -gt 0 ]]; then
                log_info "  ${service}: ${errors} errors in last 5 minutes"
            fi
        fi
    done
}

# Check database connectivity
check_database_connectivity() {
    log_section "Database Connectivity"

    # Source .env for credentials
    if [[ -f "${PROJECT_ROOT}/.env" ]]; then
        # shellcheck disable=SC1091
        source "${PROJECT_ROOT}/.env"

        # Test usermgmt database
        if docker exec mailserver-mariadb mysql \
            -u usermgmt \
            -p"${USERMGMT_DB_PASSWORD}" \
            -e "SELECT COUNT(*) FROM users;" \
            mailserver_usermgmt &>/dev/null; then
            log_info "✓ Usermgmt database: Connected"
        else
            log_error "Usermgmt database: Connection failed"
        fi

        # Test roundcube database
        if docker exec mailserver-mariadb mysql \
            -u "${MYSQL_USER}" \
            -p"${MYSQL_PASSWORD}" \
            -e "SELECT 1;" \
            "${MYSQL_DATABASE}" &>/dev/null; then
            log_info "✓ Roundcube database: Connected"
        else
            log_error "Roundcube database: Connection failed"
        fi
    else
        log_warn ".env file not found, skipping database connectivity check"
    fi
}

# Generate summary report
generate_summary() {
    log_section "Health Check Summary"

    echo ""
    echo "==================================="
    echo "Mailserver Health Check Report"
    echo "==================================="
    echo "Timestamp: $(date)"
    echo "Critical Issues: ${CRITICAL_COUNT}"
    echo "Warnings: ${WARNING_COUNT}"
    echo ""

    if [[ ${CRITICAL_COUNT} -eq 0 && ${WARNING_COUNT} -eq 0 ]]; then
        echo -e "${GREEN}✓ All systems operational${NC}"
    else
        echo "Issues Detected:"
        for issue in "${ISSUES[@]}"; do
            echo "  ${issue}"
        done
    fi

    echo ""
}

# Send alert email (if configured)
send_alert() {
    if [[ -n "${ALERT_EMAIL}" && ${CRITICAL_COUNT} -gt 0 ]]; then
        local subject="[CRITICAL] Mailserver Health Alert - ${CRITICAL_COUNT} issues"
        local body="Mailserver health check detected ${CRITICAL_COUNT} critical issues and ${WARNING_COUNT} warnings.\n\n"
        body+="Issues:\n"
        for issue in "${ISSUES[@]}"; do
            body+="${issue}\n"
        done

        # Send via local mail (requires mail command)
        if command -v mail &> /dev/null; then
            echo -e "${body}" | mail -s "${subject}" "${ALERT_EMAIL}"
            log_info "Alert email sent to ${ALERT_EMAIL}"
        else
            log_warn "mail command not available, cannot send alert email"
        fi
    fi
}

# Main monitoring function
main() {
    log_info "========================================="
    log_info "Mailserver Health Monitoring Starting"
    log_info "========================================="

    check_container_status
    check_healthcheck_status
    check_service_ports
    check_disk_usage
    check_container_resources
    check_error_logs
    check_database_connectivity
    generate_summary
    send_alert

    # Exit with error code if critical issues found
    if [[ ${CRITICAL_COUNT} -gt 0 ]]; then
        exit 1
    fi
}

# Run main function
main
