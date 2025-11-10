#!/bin/sh
set -e

# Fix file permissions for WordPress sites on first run
if [ ! -f /var/www/html/.permissions-fixed ]; then
    echo "Fixing file permissions for all WordPress sites..."

    # Change ownership to www-data (UID 82)
    chown -R www-data:www-data /var/www/html

    # Mark as fixed to avoid running on every container start
    touch /var/www/html/.permissions-fixed

    echo "Permissions fixed successfully."
fi

# Execute original WordPress entrypoint
exec docker-entrypoint.sh "$@"
