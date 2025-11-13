#!/bin/bash
#
# WordPress Redis Object Cache Setup Script
#
# Description: Install and configure Redis Object Cache plugin for all WordPress sites
# Usage: ./setup-redis-object-cache.sh [--dry-run]
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Dry-run mode
DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}[INFO] Dry-run mode enabled${NC}"
fi

# All WordPress sites (16 sites)
declare -a SITES=(
    "fx-trader-life"
    "fx-trader-life-4line"
    "fx-trader-life-lp"
    "fx-trader-life-mfkc"
    "kuma8088-cameramanual"
    "kuma8088-cameramanual-gwpbk492"
    "kuma8088-ec02test"
    "kuma8088-elementordemo02"
    "kuma8088-elementor-demo-03"
    "kuma8088-elementor-demo-04"
    "kuma8088-elementordemo1"
    "kuma8088-test"
    "toyota-phv"
    "webmakeprofit"
    "webmakeprofit-coconala"
    "webmakesprofit"
)

# Redis configuration
REDIS_HOST="172.22.0.60"
REDIS_PORT="6379"
REDIS_DATABASE=0

# Function: Print section header
print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# Function: Print success message
print_success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

# Function: Print error message
print_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

# Function: Print info message
print_info() {
    echo -e "${YELLOW}[INFO] $1${NC}"
}

# Function: Execute command (respects dry-run)
execute() {
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY-RUN]${NC} $*"
    else
        "$@"
    fi
}

# Function: Check if Redis is running
check_redis() {
    print_header "Checking Redis Connection"

    if docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T redis redis-cli ping > /dev/null 2>&1; then
        print_success "Redis is running and responding"
        return 0
    else
        print_error "Redis is not running or not responding"
        return 1
    fi
}

# Function: Install Redis Object Cache plugin for a site
install_plugin() {
    local site=$1
    local db_name="wp_${site//-/_}"

    print_info "Installing Redis Object Cache plugin for site: $site (db: $db_name)"

    # Check if plugin is already installed
    if execute docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp plugin is-installed redis-cache --path="/var/www/html/$site" --allow-root --skip-themes 2>/dev/null; then
        print_info "Plugin already installed for $site"
    else
        execute docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
            wp plugin install redis-cache --activate --path="/var/www/html/$site" --allow-root --skip-themes
        print_success "Plugin installed for $site"
    fi
}

# Function: Configure Redis for a site
configure_redis() {
    local site=$1
    local db_index=$2

    print_info "Configuring Redis for site: $site (db index: $db_index)"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY-RUN]${NC} Would add Redis config to /var/www/html/$site/wp-config.php"
        echo "WP_REDIS_HOST=${REDIS_HOST}"
        echo "WP_REDIS_PORT=${REDIS_PORT}"
        echo "WP_REDIS_DATABASE=${db_index}"
        echo "WP_REDIS_PREFIX=${site}_"
        echo "WP_REDIS_TIMEOUT=1"
        echo "WP_REDIS_READ_TIMEOUT=1"
        echo "WP_CACHE=true"
    else
        # Check if Redis config already exists
        if docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
            grep -q "WP_REDIS_HOST" "/var/www/html/$site/wp-config.php" 2>/dev/null; then
            print_info "Redis config already exists for $site"
        else
            # Try wp-cli method first
            set +e  # Temporarily disable exit on error
            local config_success=false

            docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
                wp config set WP_REDIS_HOST "${REDIS_HOST}" --type=constant --path="/var/www/html/$site" --allow-root --skip-themes 2>&1 | grep -q "^Success:" && config_success=true

            set -e  # Re-enable exit on error

            if [ "$config_success" = true ]; then
                # Continue with wp-cli if first command succeeded
                docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
                    wp config set WP_REDIS_PORT "${REDIS_PORT}" --raw --type=constant --path="/var/www/html/$site" --allow-root --skip-themes 2>/dev/null || true
                docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
                    wp config set WP_REDIS_DATABASE "${db_index}" --raw --type=constant --path="/var/www/html/$site" --allow-root --skip-themes 2>/dev/null || true
                docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
                    wp config set WP_REDIS_PREFIX "${site}_" --type=constant --path="/var/www/html/$site" --allow-root --skip-themes 2>/dev/null || true
                docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
                    wp config set WP_REDIS_TIMEOUT 1 --raw --type=constant --path="/var/www/html/$site" --allow-root --skip-themes 2>/dev/null || true
                docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
                    wp config set WP_REDIS_READ_TIMEOUT 1 --raw --type=constant --path="/var/www/html/$site" --allow-root --skip-themes 2>/dev/null || true
                docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
                    wp config set WP_CACHE true --raw --type=constant --path="/var/www/html/$site" --allow-root --skip-themes 2>/dev/null || true
                print_success "Redis config added to wp-config.php for $site"
            else
                # Fallback: Use PHP script for non-standard wp-config.php
                print_info "Using PHP helper script for non-standard wp-config.php"

                docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
                    php /usr/local/bin/add-redis-config.php \
                    "/var/www/html/$site/wp-config.php" \
                    "${REDIS_HOST}" \
                    "${REDIS_PORT}" \
                    "${db_index}" \
                    "${site}"

                # Verify
                if docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
                    grep -q "WP_REDIS_HOST" "/var/www/html/$site/wp-config.php" 2>/dev/null; then
                    print_success "Redis config added using PHP helper for $site"
                else
                    print_error "Failed to add Redis config for $site"
                fi
            fi
        fi
    fi
}

# Function: Enable Redis Object Cache for a site
enable_cache() {
    local site=$1

    print_info "Enabling Redis Object Cache for site: $site"

    set +e  # Temporarily disable exit on error
    local enable_result
    enable_result=$(docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp redis enable --path="/var/www/html/$site" --allow-root --skip-themes 2>&1)
    local enable_exit_code=$?
    set -e  # Re-enable exit on error

    if [ $enable_exit_code -eq 0 ] || echo "$enable_result" | grep -q "already enabled"; then
        print_success "Redis Object Cache enabled for $site"
        return 0
    else
        print_error "Failed to enable Redis Object Cache for $site"
        echo "$enable_result" | head -5  # Show first 5 lines of error
        return 1
    fi
}

# Function: Check cache status for a site
check_cache_status() {
    local site=$1

    print_info "Checking cache status for site: $site"

    docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp redis status --path="/var/www/html/$site" --allow-root --skip-themes || true
}

# Main execution
main() {
    print_header "WordPress Redis Object Cache Setup"

    echo "Project Root: $PROJECT_ROOT"
    echo "Total Sites: ${#SITES[@]}"
    echo "Redis Host: $REDIS_HOST"
    echo "Redis Port: $REDIS_PORT"
    echo ""

    # Check Redis connection
    if ! check_redis; then
        print_error "Please ensure Redis container is running"
        exit 1
    fi

    # Process each site
    print_header "Setting up Redis Object Cache for all sites"

    local db_index=0
    for site in "${SITES[@]}"; do
        echo ""
        print_info "Processing site $((db_index + 1))/${#SITES[@]}: $site"
        echo "---"

        # Install plugin
        install_plugin "$site"

        # Configure Redis
        configure_redis "$site" "$db_index"

        # Enable cache
        enable_cache "$site"

        # Check status
        if [ "$DRY_RUN" = false ]; then
            check_cache_status "$site"
        fi

        print_success "Site $site setup completed"

        # Increment database index for next site
        db_index=$((db_index + 1))
    done

    print_header "Setup Complete"
    print_success "Redis Object Cache configured for all ${#SITES[@]} sites"

    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo "1. Test cache performance with: ./scripts/test-redis-performance.sh"
    echo "2. Monitor Redis: docker compose exec redis redis-cli monitor"
    echo "3. Check memory usage: docker compose exec redis redis-cli info memory"
}

# Run main function
main "$@"
