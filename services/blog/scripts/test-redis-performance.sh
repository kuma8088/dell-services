#!/bin/bash
#
# WordPress Redis Performance Test Script
#
# Description: Test WordPress performance with Redis Object Cache
# Usage: ./test-redis-performance.sh [site_name]
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

# Default test site
TEST_SITE="${1:-demo1-kuma8088}"

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

# Function: Check Redis cache status
check_cache_status() {
    print_header "Cache Status for $TEST_SITE"

    docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp redis status --path="/var/www/html/$TEST_SITE"
}

# Function: Get Redis info
get_redis_info() {
    print_header "Redis Server Info"

    docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T redis redis-cli INFO stats | grep -E "keyspace_hits|keyspace_misses|used_memory_human"
    docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T redis redis-cli INFO keyspace
}

# Function: Flush Redis cache
flush_cache() {
    print_header "Flushing Redis Cache"

    docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp redis flush --path="/var/www/html/$TEST_SITE"

    print_success "Cache flushed"
}

# Function: Benchmark database queries
benchmark_queries() {
    print_header "Benchmarking Database Queries"

    print_info "Testing query performance (5 iterations)..."

    for i in {1..5}; do
        echo -n "Iteration $i: "
        docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
            wp db query "SELECT COUNT(*) FROM wp_${TEST_SITE//-/_}.wp_posts WHERE post_status='publish';" \
            --path="/var/www/html/$TEST_SITE" 2>&1 | tail -1
    done
}

# Function: Measure page load time
measure_page_load() {
    local url=$1
    print_info "Measuring page load time for: $url"

    # Use curl to measure time
    local time_total=$(curl -o /dev/null -s -w '%{time_total}\n' "$url")
    local time_namelookup=$(curl -o /dev/null -s -w '%{time_namelookup}\n' "$url")
    local time_connect=$(curl -o /dev/null -s -w '%{time_connect}\n' "$url")
    local time_starttransfer=$(curl -o /dev/null -s -w '%{time_starttransfer}\n' "$url")

    echo "  DNS Lookup:        ${time_namelookup}s"
    echo "  TCP Connection:    ${time_connect}s"
    echo "  Time to First Byte: ${time_starttransfer}s"
    echo "  Total Time:        ${time_total}s"

    echo "$time_total"
}

# Function: Run performance test
run_performance_test() {
    print_header "Performance Test for $TEST_SITE"

    # Get site URL
    local site_url=$(docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T wordpress \
        wp option get siteurl --path="/var/www/html/$TEST_SITE" 2>/dev/null || echo "")

    if [ -z "$site_url" ]; then
        print_error "Could not get site URL for $TEST_SITE"
        return 1
    fi

    print_info "Site URL: $site_url"

    # Test 1: Cold cache (after flush)
    print_info "Test 1: Cold Cache (After Flush)"
    flush_cache
    sleep 2
    local cold_time=$(measure_page_load "$site_url")

    # Test 2: Warm cache (second request)
    print_info "Test 2: Warm Cache (Second Request)"
    sleep 1
    local warm_time_1=$(measure_page_load "$site_url")

    # Test 3: Hot cache (third request)
    print_info "Test 3: Hot Cache (Third Request)"
    sleep 1
    local warm_time_2=$(measure_page_load "$site_url")

    # Summary
    print_header "Performance Summary"
    echo "Cold Cache:  ${cold_time}s"
    echo "Warm Cache:  ${warm_time_1}s"
    echo "Hot Cache:   ${warm_time_2}s"

    # Calculate improvement
    local improvement=$(awk "BEGIN {printf \"%.1f\", ($cold_time - $warm_time_2) / $cold_time * 100}")
    echo ""
    print_success "Cache improved response time by ${improvement}%"
}

# Function: Monitor Redis in real-time
monitor_redis() {
    print_header "Redis Monitor (Ctrl+C to stop)"

    print_info "Monitoring Redis commands in real-time..."
    print_info "Open another terminal and access your WordPress site"

    docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec redis redis-cli monitor
}

# Main execution
main() {
    print_header "WordPress Redis Performance Test"

    echo "Test Site: $TEST_SITE"
    echo "Project Root: $PROJECT_ROOT"
    echo ""

    # Menu
    echo "Select test:"
    echo "1. Check cache status"
    echo "2. Get Redis info"
    echo "3. Flush cache"
    echo "4. Benchmark queries"
    echo "5. Run performance test"
    echo "6. Monitor Redis (real-time)"
    echo "7. Run all tests"
    echo ""
    read -p "Enter choice [1-7]: " choice

    case $choice in
        1)
            check_cache_status
            ;;
        2)
            get_redis_info
            ;;
        3)
            flush_cache
            ;;
        4)
            benchmark_queries
            ;;
        5)
            run_performance_test
            ;;
        6)
            monitor_redis
            ;;
        7)
            check_cache_status
            get_redis_info
            benchmark_queries
            run_performance_test
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac

    print_success "Test completed"
}

# Run main function
main "$@"
