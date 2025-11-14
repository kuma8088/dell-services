#!/bin/bash
# Script: create-portal-admin-users.sh
# Purpose: Create portal_admin users on both Blog and Mailserver MariaDB
# Date: 2025-11-14

set -e

echo "=== Creating portal_admin users on Blog and Mailserver MariaDB ==="
echo

# Check if running from correct directory
if [[ ! -f "../migrations/001_add_admin_tables.sql" ]]; then
    echo "ERROR: Please run this script from services/unified-portal/backend/scripts/"
    exit 1
fi

# Prompt for passwords
read -sp "Enter password for Blog MariaDB root user: " BLOG_ROOT_PASSWORD
echo
read -sp "Enter new password for Blog portal_admin user: " BLOG_PORTAL_PASSWORD
echo
read -sp "Enter password for Mailserver MariaDB root user: " MAIL_ROOT_PASSWORD
echo
read -sp "Enter new password for Mailserver portal_admin user: " MAIL_PORTAL_PASSWORD
echo
echo

# Create Blog MariaDB portal_admin user
echo "Creating portal_admin user on Blog MariaDB (172.20.0.30:3306)..."
docker exec -i blog-mariadb-1 mysql -u root -p"${BLOG_ROOT_PASSWORD}" <<EOF
CREATE USER IF NOT EXISTS 'portal_admin'@'%' IDENTIFIED BY '${BLOG_PORTAL_PASSWORD}';
GRANT ALL PRIVILEGES ON \`wp_%\`.* TO 'portal_admin'@'%';
GRANT CREATE, DROP, ALTER ON *.* TO 'portal_admin'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON mysql.user TO 'portal_admin'@'%';
CREATE DATABASE IF NOT EXISTS blog_management CHARACTER SET utf8mb4;
GRANT ALL PRIVILEGES ON blog_management.* TO 'portal_admin'@'%';
FLUSH PRIVILEGES;
EOF

if [ $? -eq 0 ]; then
    echo "✅ Blog MariaDB portal_admin user created successfully"
else
    echo "❌ Failed to create Blog MariaDB portal_admin user"
    exit 1
fi

echo

# Create Mailserver MariaDB portal_admin user
echo "Creating portal_admin user on Mailserver MariaDB (172.20.0.60:3306)..."
docker exec -i mailserver-mariadb-1 mysql -u root -p"${MAIL_ROOT_PASSWORD}" <<EOF
CREATE USER IF NOT EXISTS 'portal_admin'@'%' IDENTIFIED BY '${MAIL_PORTAL_PASSWORD}';
GRANT ALL PRIVILEGES ON \`mailserver_%\`.* TO 'portal_admin'@'%';
GRANT CREATE, DROP, ALTER ON *.* TO 'portal_admin'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON mysql.user TO 'portal_admin'@'%';
FLUSH PRIVILEGES;
EOF

if [ $? -eq 0 ]; then
    echo "✅ Mailserver MariaDB portal_admin user created successfully"
else
    echo "❌ Failed to create Mailserver MariaDB portal_admin user"
    exit 1
fi

echo
echo "=== All portal_admin users created successfully ==="
echo
echo "Next steps:"
echo "1. Add these passwords to .env file:"
echo "   BLOG_DB_PASSWORD='${BLOG_PORTAL_PASSWORD}'"
echo "   MAIL_DB_PASSWORD='${MAIL_PORTAL_PASSWORD}'"
echo "2. Run generate-encryption-key.sh to generate ENCRYPTION_KEY"
echo "3. Run migration SQL files in backend/migrations/"
