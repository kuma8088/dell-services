-- Migration: 001_add_admin_tables.sql
-- Purpose: Add admin_users, password_reset_tokens, and db_credentials tables
-- Database: blog_management (Blog MariaDB)
-- Date: 2025-11-14

-- Admin users table (Portal administrators)
CREATE TABLE IF NOT EXISTS admin_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL COMMENT 'Admin username',
    email VARCHAR(255) UNIQUE NOT NULL COMMENT 'Admin email address',
    password_hash VARCHAR(255) NOT NULL COMMENT 'Bcrypt password hash',
    full_name VARCHAR(100) COMMENT 'Admin full name',
    is_active BOOLEAN DEFAULT TRUE NOT NULL COMMENT 'Account active status',
    is_superuser BOOLEAN DEFAULT FALSE NOT NULL COMMENT 'Superuser privileges',
    last_login DATETIME COMMENT 'Last login timestamp',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Password reset tokens table
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL COMMENT 'Email of user requesting password reset',
    token_hash VARCHAR(255) UNIQUE NOT NULL COMMENT 'SHA256 hash of reset token',
    expires_at DATETIME NOT NULL COMMENT 'Token expiration time (1 hour from creation)',
    used BOOLEAN DEFAULT FALSE COMMENT 'Whether token has been used',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_token_hash (token_hash),
    INDEX idx_user_email (user_email),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Database credentials table (encrypted passwords for database connections)
CREATE TABLE IF NOT EXISTS db_credentials (
    id INT AUTO_INCREMENT PRIMARY KEY,
    target VARCHAR(20) NOT NULL COMMENT 'blog or mailserver',
    database_name VARCHAR(100) NOT NULL,
    username VARCHAR(100) NOT NULL,
    encrypted_password TEXT NOT NULL COMMENT 'Fernet encrypted password',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_target_db_user (target, database_name, username),
    INDEX idx_target (target),
    INDEX idx_database_name (database_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
