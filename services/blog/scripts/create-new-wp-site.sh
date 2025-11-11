#!/bin/bash
#
# New WordPress Site Creation Script
# Purpose: Automated creation of new WordPress sites with all required configurations
# Author: Claude Code
# Date: 2025-11-11
#
# This script automates:
# 1. Database creation
# 2. WordPress installation
# 3. WP Mail SMTP configuration (automatic)
# 4. Nginx configuration generation
# 5. Cloudflared configuration reminder
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="${HOME}/.wp-site-creation.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

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

log_step() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$*${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# ============================================================================
# Configuration
# ============================================================================

# Default SMTP host
DEFAULT_SMTP_HOST="dell-workstation.tail67811d.ts.net"
DEFAULT_SMTP_PORT="587"

# WordPress install defaults
DEFAULT_WP_VERSION="latest"
DEFAULT_WP_LOCALE="ja"

# ============================================================================
# Helper Functions
# ============================================================================

show_usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Create a new WordPress site with automated configuration

OPTIONS:
    --interactive       Run in interactive mode (default)
    --non-interactive   Run with pre-configured values (for automation)
    --help              Show this help message

INTERACTIVE MODE:
    Prompts for all required information step by step

EXAMPLE:
    # Interactive site creation
    $0

    # View log after creation
    tail -f ~/.wp-site-creation.log

EOF
    exit 0
}

validate_site_path() {
    local site_path="$1"

    # Check if site path is empty
    if [ -z "$site_path" ]; then
        log_error "Site path cannot be empty"
        return 1
    fi

    # Check if site already exists
    if docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        test -d "/var/www/html/$site_path" 2>/dev/null; then
        log_error "Site path already exists: $site_path"
        return 1
    fi

    return 0
}

validate_domain() {
    local domain="$1"

    # Basic domain validation
    if ! echo "$domain" | grep -qE '^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'; then
        log_error "Invalid domain format: $domain"
        return 1
    fi

    return 0
}

validate_email() {
    local email="$1"

    # Basic email validation
    if ! echo "$email" | grep -qE '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'; then
        log_error "Invalid email format: $email"
        return 1
    fi

    return 0
}

generate_db_prefix() {
    local site_path="$1"

    # Convert site-path to wp_site_path format
    echo "wp_$(echo "$site_path" | sed 's/-/_/g')"
}

detect_base_domain() {
    local full_domain="$1"

    # Extract base domain (e.g., kuma8088.com from blog.kuma8088.com/test)
    local domain_only=$(echo "$full_domain" | sed 's|/.*||')

    # Get the last two parts (domain.tld)
    echo "$domain_only" | awk -F. '{print $(NF-1)"."$NF}'
}

# ============================================================================
# Interactive Input
# ============================================================================

collect_site_info() {
    log_step "Step 1: Site Information"

    # Site path
    while true; do
        echo -e "${CYAN}Enter site path (e.g., 'kuma8088-new-site'):${NC}"
        read -r SITE_PATH
        if validate_site_path "$SITE_PATH"; then
            break
        fi
    done

    # Generate default DB prefix
    DB_PREFIX=$(generate_db_prefix "$SITE_PATH")
    echo -e "${CYAN}Database prefix [${DB_PREFIX}]:${NC}"
    read -r user_db_prefix
    if [ -n "$user_db_prefix" ]; then
        DB_PREFIX="$user_db_prefix"
    fi

    # Domain
    while true; do
        echo -e "${CYAN}Enter domain (e.g., 'blog.kuma8088.com/new-site' or 'new-site.com'):${NC}"
        read -r DOMAIN
        if validate_domain "$(echo "$DOMAIN" | sed 's|/.*||')"; then
            break
        fi
    done

    # Detect base domain for email
    BASE_DOMAIN=$(detect_base_domain "$DOMAIN")
    DEFAULT_FROM_EMAIL="noreply@${BASE_DOMAIN}"

    # From email
    while true; do
        echo -e "${CYAN}From email address [${DEFAULT_FROM_EMAIL}]:${NC}"
        read -r FROM_EMAIL
        if [ -z "$FROM_EMAIL" ]; then
            FROM_EMAIL="$DEFAULT_FROM_EMAIL"
        fi
        if validate_email "$FROM_EMAIL"; then
            break
        fi
    done

    # WordPress admin info
    echo -e "${CYAN}WordPress admin username:${NC}"
    read -r WP_ADMIN_USER

    echo -e "${CYAN}WordPress admin password:${NC}"
    read -rs WP_ADMIN_PASS
    echo ""

    echo -e "${CYAN}WordPress admin email:${NC}"
    read -r WP_ADMIN_EMAIL

    echo -e "${CYAN}Site title:${NC}"
    read -r SITE_TITLE

    # SMTP settings
    echo -e "${CYAN}SMTP host [${DEFAULT_SMTP_HOST}]:${NC}"
    read -r SMTP_HOST
    if [ -z "$SMTP_HOST" ]; then
        SMTP_HOST="$DEFAULT_SMTP_HOST"
    fi

    echo -e "${CYAN}SMTP port [${DEFAULT_SMTP_PORT}]:${NC}"
    read -r SMTP_PORT
    if [ -z "$SMTP_PORT" ]; then
        SMTP_PORT="$DEFAULT_SMTP_PORT"
    fi

    # Confirmation
    log_step "Configuration Summary"
    cat <<EOF
Site Path:        $SITE_PATH
DB Prefix:        $DB_PREFIX
Domain:           $DOMAIN
From Email:       $FROM_EMAIL
SMTP Host:        $SMTP_HOST:$SMTP_PORT

WordPress Admin:  $WP_ADMIN_USER
Admin Email:      $WP_ADMIN_EMAIL
Site Title:       $SITE_TITLE
EOF

    echo -e "${YELLOW}Proceed with site creation? (yes/no):${NC}"
    read -r confirmation
    if [ "$confirmation" != "yes" ]; then
        log_error "Site creation cancelled by user"
        exit 1
    fi
}

# ============================================================================
# Site Creation Functions
# ============================================================================

create_database() {
    log_step "Step 2: Creating Database"

    local db_name="${DB_PREFIX}"

    log_info "Creating database: $db_name"

    # Create database
    if docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T mariadb \
        mysql -uroot -p"${MYSQL_ROOT_PASSWORD:-rootpassword}" \
        -e "CREATE DATABASE IF NOT EXISTS \`${db_name}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Database created: $db_name"
    else
        log_error "Failed to create database"
        return 1
    fi

    # Grant privileges (assuming WordPress DB user already exists)
    log_info "Granting privileges to WordPress user"
    docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T mariadb \
        mysql -uroot -p"${MYSQL_ROOT_PASSWORD:-rootpassword}" \
        -e "GRANT ALL PRIVILEGES ON \`${db_name}\`.* TO 'wordpress'@'%'; FLUSH PRIVILEGES;" 2>&1 | tee -a "$LOG_FILE"

    log_success "Database privileges configured"
}

install_wordpress() {
    log_step "Step 3: Installing WordPress"

    local site_url="https://${DOMAIN}"

    log_info "Creating WordPress directory: $SITE_PATH"
    docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        mkdir -p "/var/www/html/${SITE_PATH}" 2>&1 | tee -a "$LOG_FILE"

    log_info "Downloading WordPress core files..."
    if docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp core download --path="/var/www/html/${SITE_PATH}" --locale="${DEFAULT_WP_LOCALE}" --allow-root 2>&1 | tee -a "$LOG_FILE"; then
        log_success "WordPress core downloaded"
    else
        log_error "Failed to download WordPress core"
        return 1
    fi

    log_info "Creating wp-config.php..."
    docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp config create \
        --path="/var/www/html/${SITE_PATH}" \
        --dbname="${DB_PREFIX}" \
        --dbuser="wordpress" \
        --dbpass="${MYSQL_PASSWORD:-wordpresspassword}" \
        --dbhost="mariadb" \
        --dbprefix="${DB_PREFIX}_" \
        --allow-root 2>&1 | tee -a "$LOG_FILE"

    log_info "Installing WordPress..."
    if docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp core install \
        --path="/var/www/html/${SITE_PATH}" \
        --url="${site_url}" \
        --title="${SITE_TITLE}" \
        --admin_user="${WP_ADMIN_USER}" \
        --admin_password="${WP_ADMIN_PASS}" \
        --admin_email="${WP_ADMIN_EMAIL}" \
        --allow-root 2>&1 | tee -a "$LOG_FILE"; then
        log_success "WordPress installed successfully"
    else
        log_error "Failed to install WordPress"
        return 1
    fi

    log_info "Setting correct permissions..."
    docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        chown -R www-data:www-data "/var/www/html/${SITE_PATH}" 2>&1 | tee -a "$LOG_FILE"

    log_success "WordPress installation complete"
}

configure_wp_mail_smtp() {
    log_step "Step 4: Configuring WP Mail SMTP"

    local site_url="https://${DOMAIN}"

    log_info "Installing WP Mail SMTP plugin..."
    if docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp plugin install wp-mail-smtp --activate --allow-root --url="${site_url}" 2>&1 | tee -a "$LOG_FILE"; then
        log_success "WP Mail SMTP plugin installed"
    else
        log_warning "Plugin installation failed, trying to activate if already installed..."
        docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
            wp plugin activate wp-mail-smtp --allow-root --url="${site_url}" 2>&1 | tee -a "$LOG_FILE"
    fi

    log_info "Configuring SMTP settings..."

    local smtp_config=$(cat <<EOF
{
    "mail": {
        "from_email": "$FROM_EMAIL",
        "from_name": "WordPress Notification",
        "mailer": "smtp",
        "return_path": true
    },
    "smtp": {
        "host": "$SMTP_HOST",
        "port": $SMTP_PORT,
        "encryption": "tls",
        "autotls": true,
        "auth": false
    }
}
EOF
)

    if docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp option update wp_mail_smtp "$smtp_config" --format=json --allow-root --url="${site_url}" 2>&1 | tee -a "$LOG_FILE"; then
        log_success "SMTP configuration complete"
    else
        log_error "Failed to configure SMTP"
        return 1
    fi
}

generate_nginx_config() {
    log_step "Step 5: Nginx Configuration"

    log_warning "Nginx configuration needs manual setup"
    log_info "Add the following to your Nginx configuration:"

    cat <<EOF

# Configuration for $SITE_PATH ($DOMAIN)
# Add this to the appropriate Nginx config file

location /${SITE_PATH}/ {
    alias /var/www/html/${SITE_PATH}/;
    index index.php;

    try_files \$uri \$uri/ @${SITE_PATH//-/_};

    location ~ \.php$ {
        fastcgi_pass wordpress:9000;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME /var/www/html/${SITE_PATH}\$fastcgi_script_name;
        include fastcgi_params;
        fastcgi_param HTTPS on;
        fastcgi_param HTTP_X_FORWARDED_PROTO https;
    }
}

location @${SITE_PATH//-/_} {
    rewrite ^/${SITE_PATH}/(.*)$ /${SITE_PATH}/index.php?\$1 last;
}

EOF

    log_info "After adding Nginx config, run:"
    echo -e "  ${CYAN}docker compose exec nginx nginx -t${NC}"
    echo -e "  ${CYAN}docker compose exec nginx nginx -s reload${NC}"
}

generate_site_summary() {
    log_step "Site Creation Complete!"

    local summary_file="${HOME}/.wp-site-${SITE_PATH}-summary.txt"

    cat > "$summary_file" <<EOF
WordPress Site Creation Summary
================================

Site Path:        $SITE_PATH
Domain:           $DOMAIN
Created:          $(date '+%Y-%m-%d %H:%M:%S')

Database:         $DB_PREFIX
DB Prefix:        ${DB_PREFIX}_

WordPress Admin:  $WP_ADMIN_USER
Admin Email:      $WP_ADMIN_EMAIL
Site Title:       $SITE_TITLE

SMTP Config:
  From Email:     $FROM_EMAIL
  Host:           $SMTP_HOST:$SMTP_PORT
  Encryption:     TLS
  Auth:           No (trusted relay)

Next Steps:
-----------
1. Add Nginx configuration (see output above)
2. Reload Nginx:
   docker compose exec nginx nginx -s reload

3. Add to Cloudflare Tunnel:
   - Edit config/cloudflared/config.yml
   - Add hostname mapping for $DOMAIN

4. Test site:
   - Access: https://$DOMAIN
   - Login: https://$DOMAIN/wp-admin

5. Test email:
   cd $PROJECT_ROOT
   ./scripts/setup-wp-mail-smtp.sh --test-email your-email@example.com

Log File: $LOG_FILE
Summary:  $summary_file
EOF

    cat "$summary_file"
    log_success "Summary saved to: $summary_file"
}

# ============================================================================
# Main Function
# ============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                show_usage
                ;;
            --interactive|--non-interactive)
                # Currently only interactive mode is implemented
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                ;;
        esac
    done

    # Banner
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║   WordPress Site Creation Wizard          ║${NC}"
    echo -e "${CYAN}║   Automated setup with WP Mail SMTP       ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
    echo ""

    log_info "Starting site creation wizard..."

    # Check prerequisites
    if ! docker compose -f "$PROJECT_ROOT/docker-compose.yml" ps | grep -q "wordpress.*Up"; then
        log_error "WordPress container is not running"
        exit 1
    fi

    # Collect information
    collect_site_info

    # Execute creation steps
    create_database || exit 1
    install_wordpress || exit 1
    configure_wp_mail_smtp || exit 1
    generate_nginx_config

    # Generate summary
    generate_site_summary

    log_success "Site creation completed successfully!"
    log_info "Full log: $LOG_FILE"

    echo ""
    echo -e "${GREEN}✓ Site created: $SITE_PATH${NC}"
    echo -e "${YELLOW}⚠ Don't forget to configure Nginx and Cloudflare Tunnel!${NC}"
    echo ""
}

# ============================================================================
# Script Entry Point
# ============================================================================

main "$@"
