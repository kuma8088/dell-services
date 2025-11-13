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
    "kuma8088"
    "demo1-kuma8088"
    "webmakeprofit"
    "uminomoto-shoyu"
    "akihide-shiraki-fc"
    "kodomo-toushi"
    "moshilog"
    "tousi-mama"
    "furusato-media"
    "kosodate-genki"
    "warakuwork"
    "jissenjournalism"
    "lachic-style"
    "kuma8088-life"
    "kuma8088-money"
    "kuma8088-blog"
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
        wp plugin is-installed redis-cache --path="/var/www/html/$site" 2>/dev/null; then
        print_info "Plugin already installed for $site"
    else
        execute docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
            wp plugin install redis-cache --activate --path="/var/www/html/$site"
        print_success "Plugin installed for $site"
    fi
}

# Function: Configure Redis for a site
configure_redis() {
    local site=$1
    local db_index=$2

    print_info "Configuring Redis for site: $site (db index: $db_index)"

    # Add Redis configuration to wp-config.php
    local redis_config="
// Redis Object Cache Configuration
define('WP_REDIS_HOST', '${REDIS_HOST}');
define('WP_REDIS_PORT', ${REDIS_PORT});
define('WP_REDIS_DATABASE', ${db_index});
define('WP_REDIS_PREFIX', '${site}_');
define('WP_REDIS_TIMEOUT', 1);
define('WP_REDIS_READ_TIMEOUT', 1);
define('WP_CACHE', true);
"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY-RUN]${NC} Would add Redis config to /var/www/html/$site/wp-config.php"
        echo "$redis_config"
    else
        # Check if Redis config already exists
        if docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
            grep -q "WP_REDIS_HOST" "/var/www/html/$site/wp-config.php" 2>/dev/null; then
            print_info "Redis config already exists for $site"
        else
            # Add Redis config before "/* That's all, stop editing! */"
            docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
                sed -i "/\/\* That's all, stop editing! \*\//i $redis_config" \
                "/var/www/html/$site/wp-config.php"
            print_success "Redis config added to wp-config.php for $site"
        fi
    fi
}

# Function: Enable Redis Object Cache for a site
enable_cache() {
    local site=$1

    print_info "Enabling Redis Object Cache for site: $site"

    execute docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp redis enable --path="/var/www/html/$site"

    print_success "Redis Object Cache enabled for $site"
}

# Function: Check cache status for a site
check_cache_status() {
    local site=$1

    print_info "Checking cache status for site: $site"

    docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp redis status --path="/var/www/html/$site" || true
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
