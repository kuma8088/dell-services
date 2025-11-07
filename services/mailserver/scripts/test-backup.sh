#!/bin/bash
#
# test-backup.sh - Backup System Test Suite (TDD)
# Version: 1.1
#
# Purpose: Test-Driven Development for backup/restore system
# Usage: ./test-backup.sh
#
# Changelog:
# - v1.1 (2025-11-07): Fixed test assertions - removed || true from test 7.1 and 8.1
#                      to ensure proper failure detection when Usage: is missing
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test result tracking
FAILED_TESTS=()

# ==================== Helper Functions ====================
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

assert_true() {
    local test_name="$1"
    local condition="$2"
    local message="${3:-}"

    TESTS_RUN=$((TESTS_RUN + 1))

    if bash -c "$condition" 2>/dev/null; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        echo -e "${GREEN}✓${NC} PASS: ${test_name}"
        return 0
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("${test_name}")
        echo -e "${RED}✗${NC} FAIL: ${test_name}"
        if [ -n "${message}" ]; then
            log_error "  ${message}"
        fi
        return 1
    fi
}

assert_file_exists() {
    local test_name="$1"
    local file_path="$2"

    assert_true "${test_name}" "[ -f '${file_path}' ]" "File not found: ${file_path}"
}

assert_dir_exists() {
    local test_name="$1"
    local dir_path="$2"

    assert_true "${test_name}" "[ -d '${dir_path}' ]" "Directory not found: ${dir_path}"
}

assert_executable() {
    local test_name="$1"
    local file_path="$2"

    assert_true "${test_name}" "[ -x '${file_path}' ]" "File not executable: ${file_path}"
}

assert_contains() {
    local test_name="$1"
    local file_path="$2"
    local pattern="$3"

    assert_true "${test_name}" "grep -q '${pattern}' '${file_path}'" "Pattern not found in ${file_path}: ${pattern}"
}

# ==================== Test Suites ====================

test_suite_1_prerequisites() {
    log_info "========================================="
    log_info "Test Suite 1: Prerequisites"
    log_info "========================================="

    # Test 1.1: Scripts directory
    assert_dir_exists "1.1: Scripts directory exists" \
        "/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts"

    # Test 1.2: Backup script exists
    assert_file_exists "1.2: backup-mailserver.sh exists" \
        "/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-mailserver.sh"

    # Test 1.3: Backup script is executable
    assert_executable "1.3: backup-mailserver.sh is executable" \
        "/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-mailserver.sh"

    # Test 1.4: Restore script exists
    assert_file_exists "1.4: restore-mailserver.sh exists" \
        "/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/restore-mailserver.sh"

    # Test 1.5: Restore script is executable
    assert_executable "1.5: restore-mailserver.sh is executable" \
        "/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/restore-mailserver.sh"

    # Test 1.6: Config file exists
    assert_file_exists "1.6: backup-config.sh exists" \
        "/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-config.sh"

    # Test 1.7: External HDD mounted
    assert_true "1.7: External HDD is mounted" \
        "mountpoint -q /mnt/backup-hdd" \
        "/mnt/backup-hdd is not mounted"

    # Test 1.8: External HDD is writable
    assert_true "1.8: External HDD is writable" \
        "touch /mnt/backup-hdd/.test && rm /mnt/backup-hdd/.test" \
        "/mnt/backup-hdd is not writable"

    echo ""
}

test_suite_2_script_syntax() {
    log_info "========================================="
    log_info "Test Suite 2: Script Syntax"
    log_info "========================================="

    # Test 2.1: backup-mailserver.sh syntax
    assert_true "2.1: backup-mailserver.sh syntax is valid" \
        "bash -n /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-mailserver.sh" \
        "Syntax error in backup-mailserver.sh"

    # Test 2.2: restore-mailserver.sh syntax
    assert_true "2.2: restore-mailserver.sh syntax is valid" \
        "bash -n /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/restore-mailserver.sh" \
        "Syntax error in restore-mailserver.sh"

    # Test 2.3: backup-config.sh syntax
    assert_true "2.3: backup-config.sh syntax is valid" \
        "bash -n /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-config.sh" \
        "Syntax error in backup-config.sh"

    echo ""
}

test_suite_3_configuration() {
    log_info "========================================="
    log_info "Test Suite 3: Configuration"
    log_info "========================================="

    # Test 3.1: MYSQL_CONTAINER is set to mailserver-mariadb
    assert_contains "3.1: MYSQL_CONTAINER is mailserver-mariadb" \
        "/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-config.sh" \
        "mailserver-mariadb"

    # Test 3.2: ADMIN_EMAIL is set
    assert_contains "3.2: ADMIN_EMAIL is configured" \
        "/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-config.sh" \
        "ADMIN_EMAIL"

    # Test 3.3: BACKUP_ROOT points to /mnt/backup-hdd/mailserver
    assert_contains "3.3: BACKUP_ROOT is /mnt/backup-hdd/mailserver" \
        "/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-config.sh" \
        "/mnt/backup-hdd/mailserver"

    # Test 3.4: Retention periods are set
    assert_contains "3.4: DAILY_RETENTION_DAYS is set" \
        "/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-config.sh" \
        "DAILY_RETENTION_DAYS"

    assert_contains "3.5: WEEKLY_RETENTION_WEEKS is set" \
        "/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-config.sh" \
        "WEEKLY_RETENTION_WEEKS"

    # Test 3.6: .my.cnf exists
    if [ -f "${HOME}/.my.cnf" ]; then
        assert_file_exists "3.6: .my.cnf exists" "${HOME}/.my.cnf"

        # Test 3.7: .my.cnf has correct permissions
        assert_true "3.7: .my.cnf has secure permissions (600)" \
            "[ \"\$(stat -c %a ${HOME}/.my.cnf)\" = \"600\" ]" \
            ".my.cnf permissions are not 600"
    else
        log_warn "3.6: .my.cnf does not exist - skipping MySQL authentication tests"
    fi

    echo ""
}

test_suite_4_docker_environment() {
    log_info "========================================="
    log_info "Test Suite 4: Docker Environment"
    log_info "========================================="

    # Test 4.1: Docker is running
    assert_true "4.1: Docker is running" \
        "docker ps >/dev/null 2>&1" \
        "Docker is not running or not accessible"

    # Test 4.2: MariaDB container exists
    assert_true "4.2: mailserver-mariadb container exists" \
        "docker ps | grep -q mailserver-mariadb" \
        "mailserver-mariadb container not found"

    # Test 4.3: Postfix container exists
    assert_true "4.3: mailserver-postfix container exists" \
        "docker ps | grep -q mailserver-postfix" \
        "mailserver-postfix container not found"

    # Test 4.4: Dovecot container exists
    assert_true "4.4: mailserver-dovecot container exists" \
        "docker ps | grep -q mailserver-dovecot" \
        "mailserver-dovecot container not found"

    echo ""
}

test_suite_5_backup_directories() {
    log_info "========================================="
    log_info "Test Suite 5: Backup Directory Structure"
    log_info "========================================="

    # Test 5.1: Backup root exists
    if [ ! -d "/mnt/backup-hdd/mailserver" ]; then
        log_warn "5.1: Creating /mnt/backup-hdd/mailserver"
        mkdir -p /mnt/backup-hdd/mailserver/{daily,weekly}
    fi
    assert_dir_exists "5.1: Backup root exists" "/mnt/backup-hdd/mailserver"

    # Test 5.2: Daily backup directory exists
    assert_dir_exists "5.2: Daily backup directory exists" \
        "/mnt/backup-hdd/mailserver/daily"

    # Test 5.3: Weekly backup directory exists
    assert_dir_exists "5.3: Weekly backup directory exists" \
        "/mnt/backup-hdd/mailserver/weekly"

    # Test 5.4: Backup root has correct permissions
    assert_true "5.4: Backup root is owned by system-admin" \
        "[ \"\$(stat -c %U /mnt/backup-hdd/mailserver)\" = \"system-admin\" ]" \
        "/mnt/backup-hdd/mailserver not owned by system-admin"

    echo ""
}

test_suite_6_backup_sources() {
    log_info "========================================="
    log_info "Test Suite 6: Backup Source Data"
    log_info "========================================="

    # Test 6.1: Mail data directory exists
    assert_dir_exists "6.1: Mail data directory exists" \
        "/opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail"

    # Test 6.2: Config directory exists
    assert_dir_exists "6.2: Config directory exists" \
        "/opt/onprem-infra-system/project-root-infra/services/mailserver/config"

    # Test 6.3: docker-compose.yml exists
    assert_file_exists "6.3: docker-compose.yml exists" \
        "/opt/onprem-infra-system/project-root-infra/services/mailserver/docker-compose.yml"

    # Test 6.4: .env file exists
    assert_file_exists "6.4: .env file exists" \
        "/opt/onprem-infra-system/project-root-infra/services/mailserver/.env"

    # Test 6.5: SSL directory exists (optional)
    if [ -d "/opt/onprem-infra-system/project-root-infra/services/mailserver/data/certbot" ]; then
        assert_dir_exists "6.5: SSL certbot directory exists" \
            "/opt/onprem-infra-system/project-root-infra/services/mailserver/data/certbot"
    else
        log_warn "6.5: SSL certbot directory does not exist - skipping"
    fi

    # Test 6.6: DKIM directory exists (optional)
    if [ -d "/opt/onprem-infra-system/project-root-infra/services/mailserver/config/opendkim" ]; then
        assert_dir_exists "6.6: DKIM opendkim directory exists" \
            "/opt/onprem-infra-system/project-root-infra/services/mailserver/config/opendkim"
    else
        log_warn "6.6: DKIM opendkim directory does not exist - skipping"
    fi

    echo ""
}

test_suite_7_dry_run_backup() {
    log_info "========================================="
    log_info "Test Suite 7: Dry-Run Backup Test"
    log_info "========================================="

    # Test 7.1: Backup script help/usage
    assert_true "7.1: Backup script can display usage" \
        "/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-mailserver.sh --help 2>&1 | grep -q 'Usage:'" \
        "Backup script does not respond to --help"

    # Test 7.2: Check for required tools
    assert_true "7.2: rsync is installed" \
        "command -v rsync >/dev/null" \
        "rsync is not installed"

    assert_true "7.3: mysqldump is available in container" \
        "docker exec mailserver-mariadb mysqldump --version >/dev/null 2>&1" \
        "mysqldump is not available in mailserver-mariadb container"

    assert_true "7.4: tar is available" \
        "command -v tar >/dev/null" \
        "tar is not installed"

    assert_true "7.5: gzip is available" \
        "command -v gzip >/dev/null" \
        "gzip is not installed"

    echo ""
}

test_suite_8_restore_validation() {
    log_info "========================================="
    log_info "Test Suite 8: Restore Script Validation"
    log_info "========================================="

    # Test 8.1: Restore script help/usage
    assert_true "8.1: Restore script can display usage" \
        "/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/restore-mailserver.sh --help 2>&1 | grep -q 'Usage:'" \
        "Restore script does not respond to --help"

    # Test 8.2: Restore script validates --from requirement
    assert_true "8.2: Restore script requires --from parameter" \
        "/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/restore-mailserver.sh 2>&1 | grep -q 'from.*required' || /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/restore-mailserver.sh 2>&1 | grep -q 'Usage:'" \
        "Restore script does not validate --from parameter"

    echo ""
}

# ==================== Main Test Execution ====================
main() {
    log_info "========================================="
    log_info "Backup System Test Suite (TDD)"
    log_info "========================================="
    log_info "Date: $(date)"
    log_info "User: $(whoami)"
    echo ""

    # Run all test suites
    test_suite_1_prerequisites
    test_suite_2_script_syntax
    test_suite_3_configuration
    test_suite_4_docker_environment
    test_suite_5_backup_directories
    test_suite_6_backup_sources
    test_suite_7_dry_run_backup
    test_suite_8_restore_validation

    # Summary
    log_info "========================================="
    log_info "Test Summary"
    log_info "========================================="
    echo "Total Tests Run:    ${TESTS_RUN}"
    echo -e "${GREEN}Tests Passed:       ${TESTS_PASSED}${NC}"
    if [ ${TESTS_FAILED} -gt 0 ]; then
        echo -e "${RED}Tests Failed:       ${TESTS_FAILED}${NC}"
        echo ""
        log_error "Failed Tests:"
        for test in "${FAILED_TESTS[@]}"; do
            echo "  - ${test}"
        done
        echo ""
        exit 1
    else
        echo -e "${GREEN}Tests Failed:       0${NC}"
        echo ""
        log_info "✓ All tests passed!"
        echo ""
        log_info "Next steps:"
        echo "  1. Create ~/.my.cnf with MySQL credentials"
        echo "  2. Run: ./backup-mailserver.sh --daily"
        echo "  3. Verify backup: ls -lh /mnt/backup-hdd/mailserver/daily/"
        echo ""
        exit 0
    fi
}

# Run tests
main "$@"
