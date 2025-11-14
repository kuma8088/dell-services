-- Migration: 002_add_wordpress_sites.sql
-- Purpose: Add wordpress_sites table for WordPress management
-- Database: blog_management (Blog MariaDB)
-- Date: 2025-11-14

-- WordPress sites table
CREATE TABLE IF NOT EXISTS wordpress_sites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    site_name VARCHAR(100) UNIQUE NOT NULL COMMENT 'Site identifier (e.g., kuma8088, demo1)',
    domain VARCHAR(255) UNIQUE NOT NULL COMMENT 'Full domain name (e.g., kuma8088.com, demo1.kuma8088.com)',
    database_name VARCHAR(100) NOT NULL COMMENT 'WordPress database name (e.g., wp_kuma8088)',
    php_version VARCHAR(10) NOT NULL COMMENT 'PHP version: 7.4, 8.0, 8.1, 8.2',
    enabled BOOLEAN DEFAULT TRUE COMMENT 'Whether site is active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_site_name (site_name),
    INDEX idx_domain (domain),
    INDEX idx_php_version (php_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
