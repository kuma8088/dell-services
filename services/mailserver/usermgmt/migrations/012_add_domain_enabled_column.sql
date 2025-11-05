-- Migration 012: Add enabled column to domains table
-- Purpose: Enable soft-delete functionality for domains
-- Created: 2025-11-05

-- Add enabled column
ALTER TABLE domains ADD COLUMN enabled BOOLEAN DEFAULT TRUE NOT NULL;

-- Ensure all existing domains are enabled by default
UPDATE domains SET enabled = TRUE WHERE enabled IS NULL;

-- Verification query
SELECT id, name, enabled FROM domains;
