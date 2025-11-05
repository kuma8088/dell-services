-- Migration 013 Rollback: Revert audit_logs ENUM to original values
-- Date: 2025-11-05
-- WARNING: This will fail if any domain_* actions exist in audit_logs

USE mailserver_usermgmt;

-- Revert to original ENUM values
ALTER TABLE audit_logs
MODIFY COLUMN action ENUM(
    'create',
    'update',
    'delete',
    'password_change'
) NOT NULL;

-- Verify the change
DESCRIBE audit_logs;
