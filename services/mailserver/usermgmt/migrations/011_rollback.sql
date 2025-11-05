-- Rollback Migration 011: Remove is_admin column
-- Purpose: Revert admin/user role separation
-- Created: 2025-11-05

-- Drop trigger
DROP TRIGGER IF EXISTS trg_single_admin_check;

-- Remove is_admin column
ALTER TABLE users DROP COLUMN is_admin;

-- Verification query
DESCRIBE users;
