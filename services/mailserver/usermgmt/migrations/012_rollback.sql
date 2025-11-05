-- Rollback Migration 012: Remove enabled column from domains table
-- Purpose: Revert domain soft-delete functionality
-- Created: 2025-11-05

-- Remove enabled column
ALTER TABLE domains DROP COLUMN enabled;

-- Verification query
DESCRIBE domains;
