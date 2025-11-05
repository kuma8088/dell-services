-- Migration 011: Add is_admin column to users table
-- Purpose: Enable admin/user role separation with single admin constraint
-- Created: 2025-11-05

-- Add is_admin column
ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE NOT NULL;

-- Set existing admin@kuma8088.com as admin
UPDATE users SET is_admin = TRUE WHERE email = 'admin@kuma8088.com';

-- Create trigger to enforce single admin constraint
DELIMITER $$

CREATE TRIGGER trg_single_admin_check
BEFORE UPDATE ON users
FOR EACH ROW
BEGIN
    -- Only check if trying to set is_admin to TRUE
    IF NEW.is_admin = TRUE AND OLD.is_admin = FALSE THEN
        -- Check if another admin already exists
        IF (SELECT COUNT(*) FROM users WHERE is_admin = TRUE) > 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = '管理者は1ユーザーのみ設定可能です';
        END IF;
    END IF;
END$$

DELIMITER ;

-- Verification query
SELECT email, is_admin FROM users;
