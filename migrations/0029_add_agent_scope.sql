-- =============================================================================
-- L9 Memory Substrate - Add 'agent' Scope
-- Migration: 0029_add_agent_scope.sql
-- Version: 2.3.0
-- Date: 2026-02-02
-- =============================================================================
--
-- PURPOSE: Add 'agent' scope to packet_store_scope_check constraint
--   - World Model and Seed Loader use scope='agent' for agent-specific packets
--   - Current constraint only allows: developer, global, l-private
--   - This migration adds 'agent' to the allowed scopes
--
-- CONTEXT: Error was "violates check constraint packet_store_scope_check"
--          when inserting seed data with scope='agent'
--
-- =============================================================================

BEGIN;

-- =============================================================================
-- STEP 1: Drop existing scope CHECK constraint
-- =============================================================================
ALTER TABLE packet_store
  DROP CONSTRAINT IF EXISTS packet_store_scope_check;

-- =============================================================================
-- STEP 2: Add new CHECK constraint with 'agent' scope included
-- =============================================================================
ALTER TABLE packet_store
  ADD CONSTRAINT packet_store_scope_check
  CHECK (scope IN ('developer', 'global', 'l-private', 'agent'));

-- =============================================================================
-- STEP 3: Update RLS policy to include 'agent' scope
-- =============================================================================
DROP POLICY IF EXISTS packet_store_scope_access ON packet_store;
CREATE POLICY packet_store_scope_access ON packet_store
    FOR ALL
    USING (
        scope IS NULL
        OR scope IN ('developer', 'global', 'agent')
        OR (scope = 'l-private' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('l9_system', 'platform_admin'))
    )
    WITH CHECK (
        scope IS NULL
        OR scope IN ('developer', 'global', 'agent')
        OR (scope = 'l-private' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('l9_system', 'platform_admin'))
    );

-- =============================================================================
-- STEP 4: Verification
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 0029 completed successfully';
    RAISE NOTICE '   - Added "agent" scope to packet_store_scope_check constraint';
    RAISE NOTICE '   - Updated RLS policy to allow "agent" scope';
    RAISE NOTICE '   - Valid scopes are now: developer, global, l-private, agent';
END
$$;

COMMIT;

-- =============================================================================
-- END MIGRATION 0029
-- =============================================================================
