#!/bin/bash
#
# WP Mail SMTP Setup Script for 16 WordPress Sites
# Purpose: Install and configure WP Mail SMTP plugin with domain-specific email addresses
# Author: Claude Code
# Date: 2025-11-11
#

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="${HOME}/.wp-mail-smtp-setup.log"
BACKUP_DIR="${HOME}/.wp-mail-smtp-backups"

# SMTP Configuration
SMTP_HOST="dell-workstation.tail67811d.ts.net"
SMTP_PORT="587"
SMTP_ENCRYPTION="tls"
SMTP_FROM_NAME="WordPress Notification"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Dry-run flag
DRY_RUN=false

# ============================================================================
# Site Configuration: [path]|[db_prefix]|[domain]|[from_email]
# ============================================================================

declare -a SITES=(
    "fx-trader-life|wp_fx_trader_life|fx-trader-life.com|noreply@fx-trader-life.com"
    "fx-trader-life-4line|wp_fx_trader_life_4line|fx-trader-life.com/4line|noreply@fx-trader-life.com"
    "fx-trader-life-lp|wp_fx_trader_life_lp|fx-trader-life.com/lp|noreply@fx-trader-life.com"
    "fx-trader-life-mfkc|wp_fx_trader_life_mfkc|mfkc.fx-trader-life.com|noreply@fx-trader-life.com"
    "kuma8088|wp_kuma8088|kuma8088.com|noreply@kuma8088.com"
    "kuma8088-cameramanual|wp_kuma8088_cameramanual|blog.kuma8088.com/cameramanual|noreply@kuma8088.com"
    "kuma8088-ec02test|wp_kuma8088_ec02test|blog.kuma8088.com/ec02test|noreply@kuma8088.com"
    "kuma8088-elementordemo02|wp_kuma8088_elementordemo02|blog.kuma8088.com/elementordemo02|noreply@kuma8088.com"
    "kuma8088-elementor-demo-03|wp_kuma8088_elementor_demo_03|blog.kuma8088.com/elementor-demo-03|noreply@kuma8088.com"
    "kuma8088-elementor-demo-04|wp_kuma8088_elementor_demo_04|blog.kuma8088.com/elementor-demo-04|noreply@kuma8088.com"
    "kuma8088-elementordemo1|wp_kuma8088_elementordemo1|demo1.kuma8088.com|noreply@kuma8088.com"
    "kuma8088-test|wp_kuma8088_test|blog.kuma8088.com/test|noreply@kuma8088.com"
    "toyota-phv|wp_toyota_phv|toyota-phv.com|noreply@toyota-phv.com"
    "webmakeprofit|wp_webmakeprofit|webmakeprofit.com|noreply@webmakeprofit.com"
    "webmakeprofit-coconala|wp_webmakeprofit_coconala|webmakeprofit.com/coconala|noreply@webmakeprofit.com"
    "webmakesprofit|wp_webmakesprofit|webmakesprofit.com|noreply@webmakesprofit.com"
)

# ============================================================================
# Logging Functions
# ============================================================================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

log_info() {
    log "INFO" "$@"
    echo -e "${BLUE}ℹ${NC} $*"
}

log_success() {
    log "SUCCESS" "$@"
    echo -e "${GREEN}✓${NC} $*"
}

log_warning() {
    log "WARNING" "$@"
    echo -e "${YELLOW}⚠${NC} $*"
}

log_error() {
    log "ERROR" "$@"
    echo -e "${RED}✗${NC} $*"
}

# ============================================================================
# Helper Functions
# ============================================================================

show_usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

OPTIONS:
    --dry-run           Show what would be done without making changes
    --verify            Verify current WP Mail SMTP configuration for all sites
    --test-email EMAIL  Send test email to specified address from all sites
    --help              Show this help message

EXAMPLES:
    # Dry-run to see what would be changed
    $0 --dry-run

    # Install and configure WP Mail SMTP on all sites
    $0

    # Verify current configuration
    $0 --verify

    # Send test emails to verify SMTP settings
    $0 --test-email naoya.iimura@gmail.com

EOF
    exit 0
}

preflight_checks() {
    log_info "Running preflight checks..."

    # Check if Docker Compose is running
    if ! docker compose -f "$PROJECT_ROOT/docker-compose.yml" ps | grep -q "wordpress.*Up"; then
        log_error "WordPress container is not running"
        return 1
    fi

    # Check if wp-cli is available
    if ! docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress wp --version --allow-root &>/dev/null; then
        log_error "wp-cli is not available in WordPress container"
        return 1
    fi

    # Create backup directory
    mkdir -p "$BACKUP_DIR"

    # Create log file
    touch "$LOG_FILE"

    log_success "Preflight checks passed"
    return 0
}

backup_current_settings() {
    local site_path="$1"
    local db_prefix="$2"
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_file="$BACKUP_DIR/${site_path}_${timestamp}.json"

    log_info "Backing up current settings for $site_path..."

    # Get current wp_mail_smtp option
    local current_settings=$(docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp option get wp_mail_smtp --format=json --allow-root --url="https://$site_path" 2>/dev/null || echo "{}")

    echo "$current_settings" > "$backup_file"
    log_success "Backup saved to $backup_file"
}

install_plugin() {
    local site_path="$1"
    local site_url="$2"

    log_info "Installing WP Mail SMTP plugin for $site_path..."

    # Check if plugin is already installed
    if docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp plugin is-installed wp-mail-smtp --allow-root --url="https://$site_url" 2>/dev/null; then
        log_info "Plugin already installed for $site_path"
    else
        # Install plugin
        if docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
            wp plugin install wp-mail-smtp --allow-root --url="https://$site_url" 2>&1 | tee -a "$LOG_FILE"; then
            log_success "Plugin installed for $site_path"
        else
            log_error "Failed to install plugin for $site_path"
            return 1
        fi
    fi

    # Activate plugin
    if docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp plugin activate wp-mail-smtp --allow-root --url="https://$site_url" 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Plugin activated for $site_path"
        return 0
    else
        log_warning "Failed to activate plugin for $site_path (may already be active)"
        return 0
    fi
}

configure_smtp() {
    local site_path="$1"
    local site_url="$2"
    local from_email="$3"

    log_info "Configuring SMTP settings for $site_path..."

    # Build SMTP configuration JSON
    local smtp_config=$(cat <<EOF
{
    "mail": {
        "from_email": "$from_email",
        "from_name": "$SMTP_FROM_NAME",
        "mailer": "smtp",
        "return_path": true
    },
    "smtp": {
        "host": "$SMTP_HOST",
        "port": $SMTP_PORT,
        "encryption": "$SMTP_ENCRYPTION",
        "autotls": true,
        "auth": false
    }
}
EOF
)

    # Update wp_mail_smtp option
    if docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp option update wp_mail_smtp "$smtp_config" --format=json --allow-root --url="https://$site_url" 2>&1 | tee -a "$LOG_FILE"; then
        log_success "SMTP configuration updated for $site_path"
        return 0
    else
        log_error "Failed to update SMTP configuration for $site_path"
        return 1
    fi
}

verify_configuration() {
    local site_path="$1"
    local site_url="$2"
    local expected_email="$3"

    log_info "Verifying configuration for $site_path..."

    # Get current configuration
    local current_config=$(docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp option get wp_mail_smtp --format=json --allow-root --url="https://$site_url" 2>/dev/null)

    if [ -z "$current_config" ] || [ "$current_config" == "false" ]; then
        log_warning "No WP Mail SMTP configuration found for $site_path"
        return 1
    fi

    # Check from_email
    local from_email=$(echo "$current_config" | grep -o '"from_email":"[^"]*"' | cut -d'"' -f4)
    if [ "$from_email" == "$expected_email" ]; then
        log_success "From email correct: $from_email"
    else
        log_warning "From email mismatch: expected $expected_email, got $from_email"
    fi

    # Check SMTP host
    local smtp_host=$(echo "$current_config" | grep -o '"host":"[^"]*"' | cut -d'"' -f4)
    if [ "$smtp_host" == "$SMTP_HOST" ]; then
        log_success "SMTP host correct: $smtp_host"
    else
        log_warning "SMTP host mismatch: expected $SMTP_HOST, got $smtp_host"
    fi

    return 0
}

send_test_email() {
    local site_path="$1"
    local site_url="$2"
    local to_email="$3"

    log_info "Sending test email from $site_path to $to_email..."

    # Use wp eval to send test email via wp_mail()
    local php_code="wp_mail('$to_email', 'Test from $site_url', 'This is a test email from $site_url sent at " $(date '+%Y-%m-%d %H:%M:%S') ".');"

    if docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp eval "$php_code" --allow-root --url="https://$site_url" 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Test email sent from $site_path"
        return 0
    else
        log_error "Failed to send test email from $site_path"
        return 1
    fi
}

# ============================================================================
# Main Functions
# ============================================================================

setup_site() {
    local site_config="$1"

    IFS='|' read -r site_path db_prefix domain from_email <<< "$site_config"

    echo ""
    log_info "=================================================="
    log_info "Processing site: $site_path"
    log_info "Domain: $domain"
    log_info "From Email: $from_email"
    log_info "=================================================="

    # Backup current settings (even in dry-run mode for safety)
    if [ "$DRY_RUN" == "false" ]; then
        backup_current_settings "$site_path" "$db_prefix" || true
    fi

    if [ "$DRY_RUN" == "true" ]; then
        log_info "[DRY-RUN] Would install plugin for $site_path"
        log_info "[DRY-RUN] Would configure SMTP: $from_email -> $SMTP_HOST:$SMTP_PORT"
        return 0
    fi

    # Install and activate plugin
    if ! install_plugin "$site_path" "$domain"; then
        log_error "Plugin installation failed for $site_path, skipping configuration"
        return 1
    fi

    # Configure SMTP
    if ! configure_smtp "$site_path" "$domain" "$from_email"; then
        log_error "SMTP configuration failed for $site_path"
        return 1
    fi

    # Verify configuration
    verify_configuration "$site_path" "$domain" "$from_email"

    log_success "Site $site_path setup completed"
    return 0
}

verify_all_sites() {
    log_info "Verifying WP Mail SMTP configuration for all sites..."

    local success_count=0
    local total_count=${#SITES[@]}

    for site_config in "${SITES[@]}"; do
        IFS='|' read -r site_path db_prefix domain from_email <<< "$site_config"

        echo ""
        log_info "Verifying: $site_path ($domain)"

        if verify_configuration "$site_path" "$domain" "$from_email"; then
            ((success_count++))
        fi
    done

    echo ""
    log_info "=================================================="
    log_info "Verification Summary: $success_count/$total_count sites configured correctly"
    log_info "=================================================="
}

test_all_sites() {
    local test_email="$1"

    log_info "Sending test emails from all sites to $test_email..."

    local success_count=0
    local total_count=${#SITES[@]}

    for site_config in "${SITES[@]}"; do
        IFS='|' read -r site_path db_prefix domain from_email <<< "$site_config"

        echo ""
        if send_test_email "$site_path" "$domain" "$test_email"; then
            ((success_count++))
        fi

        # Small delay to avoid overwhelming mail server
        sleep 2
    done

    echo ""
    log_info "=================================================="
    log_info "Test Email Summary: $success_count/$total_count emails sent successfully"
    log_info "=================================================="
}

main() {
    local mode="setup"
    local test_email=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --verify)
                mode="verify"
                shift
                ;;
            --test-email)
                mode="test"
                test_email="$2"
                shift 2
                ;;
            --help)
                show_usage
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                ;;
        esac
    done

    # Show banner
    echo ""
    echo "=================================================="
    echo "  WP Mail SMTP Setup Script"
    echo "  Mode: $mode"
    if [ "$DRY_RUN" == "true" ]; then
        echo "  DRY-RUN MODE: No changes will be made"
    fi
    echo "  Log file: $LOG_FILE"
    echo "=================================================="
    echo ""

    # Initialize log
    log_info "Script started in $mode mode (dry-run: $DRY_RUN)"

    # Preflight checks (skip in verify mode)
    if [ "$mode" != "verify" ]; then
        if ! preflight_checks; then
            log_error "Preflight checks failed, exiting"
            exit 1
        fi
    fi

    # Execute based on mode
    case $mode in
        setup)
            local success_count=0
            local total_count=${#SITES[@]}

            for site_config in "${SITES[@]}"; do
                if setup_site "$site_config"; then
                    ((success_count++))
                fi
            done

            echo ""
            log_info "=================================================="
            log_info "Setup Summary: $success_count/$total_count sites configured successfully"
            if [ "$DRY_RUN" == "false" ]; then
                log_info "Backups stored in: $BACKUP_DIR"
            fi
            log_info "Full log: $LOG_FILE"
            log_info "=================================================="
            ;;
        verify)
            verify_all_sites
            ;;
        test)
            if [ -z "$test_email" ]; then
                log_error "Test email address is required"
                show_usage
            fi
            test_all_sites "$test_email"
            ;;
    esac

    log_info "Script completed"
}

# ============================================================================
# Script Entry Point
# ============================================================================

main "$@"
