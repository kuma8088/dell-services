-- Migration 013: Add domain actions to audit_logs ENUM
-- Date: 2025-11-05
-- Purpose: Support domain management audit logging

USE mailserver_usermgmt;

-- Add domain-related actions to the audit_logs.action ENUM
ALTER TABLE audit_logs
MODIFY COLUMN action ENUM(
    'create',
    'update',
    'delete',
    'password_change',
    'domain_create',
    'domain_update',
    'domain_delete',
    'domain_toggle'
) NOT NULL;

-- Verify the change
DESCRIBE audit_logs;
