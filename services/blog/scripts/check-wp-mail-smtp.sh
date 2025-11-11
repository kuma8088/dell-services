#!/bin/bash
#
# WP Mail SMTP Quick Check Script
# Purpose: Quick status check for WP Mail SMTP plugin across all sites
# Author: Claude Code
# Date: 2025-11-11
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Site configuration
declare -a SITES=(
    "fx-trader-life|fx-trader-life.com|noreply@fx-trader-life.com"
    "fx-trader-life-4line|fx-trader-life.com/4line|noreply@fx-trader-life.com"
    "fx-trader-life-lp|fx-trader-life.com/lp|noreply@fx-trader-life.com"
    "fx-trader-life-mfkc|mfkc.fx-trader-life.com|noreply@fx-trader-life.com"
    "kuma8088|kuma8088.com|noreply@kuma8088.com"
    "kuma8088-cameramanual|blog.kuma8088.com/cameramanual|noreply@kuma8088.com"
    "kuma8088-ec02test|blog.kuma8088.com/ec02test|noreply@kuma8088.com"
    "kuma8088-elementordemo02|blog.kuma8088.com/elementordemo02|noreply@kuma8088.com"
    "kuma8088-elementor-demo-03|blog.kuma8088.com/elementor-demo-03|noreply@kuma8088.com"
    "kuma8088-elementor-demo-04|blog.kuma8088.com/elementor-demo-04|noreply@kuma8088.com"
    "kuma8088-elementordemo1|demo1.kuma8088.com|noreply@kuma8088.com"
    "kuma8088-test|blog.kuma8088.com/test|noreply@kuma8088.com"
    "toyota-phv|toyota-phv.com|noreply@toyota-phv.com"
    "webmakeprofit|webmakeprofit.com|noreply@webmakeprofit.com"
    "webmakeprofit-coconala|webmakeprofit.com/coconala|noreply@webmakeprofit.com"
    "webmakesprofit|webmakesprofit.com|noreply@webmakesprofit.com"
)

show_usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Quick check script for WP Mail SMTP plugin status

OPTIONS:
    --detailed      Show detailed configuration for each site
    --json          Output results in JSON format
    --help          Show this help message

EXAMPLES:
    # Quick status check
    $0

    # Detailed configuration view
    $0 --detailed

    # JSON output for scripting
    $0 --json

EOF
    exit 0
}

check_plugin_status() {
    local domain="$1"

    docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp plugin is-installed wp-mail-smtp --allow-root --url="https://$domain" 2>/dev/null
}

check_plugin_active() {
    local domain="$1"

    docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp plugin is-active wp-mail-smtp --allow-root --url="https://$domain" 2>/dev/null
}

get_from_email() {
    local domain="$1"

    docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp option get wp_mail_smtp --format=json --allow-root --url="https://$domain" 2>/dev/null | \
        grep -o '"from_email":"[^"]*"' | cut -d'"' -f4 || echo "N/A"
}

get_smtp_host() {
    local domain="$1"

    docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp option get wp_mail_smtp --format=json --allow-root --url="https://$domain" 2>/dev/null | \
        grep -o '"host":"[^"]*"' | cut -d'"' -f4 || echo "N/A"
}

quick_check() {
    echo ""
    echo "=================================================="
    echo "  WP Mail SMTP Quick Status Check"
    echo "=================================================="
    echo ""

    printf "%-30s %-12s %-10s %-35s\n" "Site" "Installed" "Active" "From Email"
    printf "%-30s %-12s %-10s %-35s\n" "----" "---------" "------" "----------"

    local installed_count=0
    local active_count=0
    local configured_count=0

    for site_config in "${SITES[@]}"; do
        IFS='|' read -r site_path domain expected_email <<< "$site_config"

        # Check installation
        if check_plugin_status "$domain"; then
            installed="✓"
            ((installed_count++))
        else
            installed="✗"
        fi

        # Check activation
        if check_plugin_active "$domain"; then
            active="✓"
            ((active_count++))
        else
            active="✗"
        fi

        # Get from email
        from_email=$(get_from_email "$domain")

        # Check if configured correctly
        if [ "$from_email" == "$expected_email" ]; then
            ((configured_count++))
            email_status="${GREEN}$from_email${NC}"
        elif [ "$from_email" == "N/A" ]; then
            email_status="${RED}Not configured${NC}"
        else
            email_status="${YELLOW}$from_email (expected: $expected_email)${NC}"
        fi

        printf "%-30s %-12s %-10s " "$site_path" "$installed" "$active"
        echo -e "$email_status"
    done

    echo ""
    echo "=================================================="
    echo "Summary:"
    echo "  Installed: $installed_count/${#SITES[@]}"
    echo "  Active:    $active_count/${#SITES[@]}"
    echo "  Configured correctly: $configured_count/${#SITES[@]}"
    echo "=================================================="
    echo ""
}

detailed_check() {
    echo ""
    echo "=================================================="
    echo "  WP Mail SMTP Detailed Configuration"
    echo "=================================================="

    for site_config in "${SITES[@]}"; do
        IFS='|' read -r site_path domain expected_email <<< "$site_config"

        echo ""
        echo "Site: $site_path"
        echo "Domain: $domain"
        echo "----------------------------------------"

        # Plugin status
        if check_plugin_status "$domain"; then
            echo -e "Plugin Installed: ${GREEN}✓${NC}"
        else
            echo -e "Plugin Installed: ${RED}✗${NC}"
            continue
        fi

        if check_plugin_active "$domain"; then
            echo -e "Plugin Active:    ${GREEN}✓${NC}"
        else
            echo -e "Plugin Active:    ${RED}✗${NC}"
        fi

        # Configuration
        from_email=$(get_from_email "$domain")
        smtp_host=$(get_smtp_host "$domain")

        echo "From Email: $from_email"
        if [ "$from_email" == "$expected_email" ]; then
            echo -e "  ${GREEN}✓ Correct${NC}"
        else
            echo -e "  ${YELLOW}⚠ Expected: $expected_email${NC}"
        fi

        echo "SMTP Host: $smtp_host"
        if [ "$smtp_host" == "dell-workstation.tail67811d.ts.net" ]; then
            echo -e "  ${GREEN}✓ Correct${NC}"
        else
            echo -e "  ${YELLOW}⚠ Expected: dell-workstation.tail67811d.ts.net${NC}"
        fi
    done

    echo ""
    echo "=================================================="
}

json_output() {
    echo "{"
    echo '  "timestamp": "'$(date -u '+%Y-%m-%dT%H:%M:%SZ')'",'
    echo '  "sites": ['

    local first=true
    for site_config in "${SITES[@]}"; do
        IFS='|' read -r site_path domain expected_email <<< "$site_config"

        if [ "$first" = true ]; then
            first=false
        else
            echo ","
        fi

        installed=$(check_plugin_status "$domain" && echo "true" || echo "false")
        active=$(check_plugin_active "$domain" && echo "true" || echo "false")
        from_email=$(get_from_email "$domain")
        smtp_host=$(get_smtp_host "$domain")

        cat <<EOF
    {
      "site_path": "$site_path",
      "domain": "$domain",
      "expected_email": "$expected_email",
      "plugin_installed": $installed,
      "plugin_active": $active,
      "configured_from_email": "$from_email",
      "smtp_host": "$smtp_host",
      "correctly_configured": $([ "$from_email" == "$expected_email" ] && echo "true" || echo "false")
    }
EOF
    done

    echo ""
    echo "  ]"
    echo "}"
}

main() {
    local mode="quick"

    while [[ $# -gt 0 ]]; do
        case $1 in
            --detailed)
                mode="detailed"
                shift
                ;;
            --json)
                mode="json"
                shift
                ;;
            --help)
                show_usage
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                ;;
        esac
    done

    case $mode in
        quick)
            quick_check
            ;;
        detailed)
            detailed_check
            ;;
        json)
            json_output
            ;;
    esac
}

main "$@"
