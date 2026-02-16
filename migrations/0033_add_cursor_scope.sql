-- =============================================================================
-- L9 Memory Substrate - Add 'cursor' scope for Cursor IDE isolation
-- Migration: 0033_add_cursor_scope.sql
-- Version: 2.5.0
-- Date: 2026-02-13
-- =============================================================================
--
-- PURPOSE: Add 'cursor' scope to packet_store for Cursor IDE RLS isolation
--   - ADR-0005 defines scope-based isolation: Cursor uses scope='cursor'
--   - cursor_memory_kernel.py sets app.role='cursor' explicitly
--   - Migration 0016 originally included 'cursor' but it was dropped during cleanup
--   - This migration restores it alongside the existing scopes
--
-- CONTEXT: Cursor IDE memory writes were using scope='developer' as a workaround
--          because 'cursor' was not in the CHECK constraint. This migration fixes
--          the database to match the designed RLS model.
--
-- =============================================================================

-- =============================================================================
-- STEP 1: Drop existing CHECK constraint
-- =============================================================================
ALTER TABLE packet_store
  DROP CONSTRAINT IF EXISTS packet_store_scope_check;

-- =============================================================================
-- STEP 2: Recreate with 'cursor' scope added
-- =============================================================================
ALTER TABLE packet_store
  ADD CONSTRAINT packet_store_scope_check
  CHECK (scope IN ('developer', 'global', 'l-private', 'agent', 'cursor'));

-- =============================================================================
-- STEP 3: Update RLS policy to allow 'cursor' scope
--   - cursor scope is accessible by cursor_user role and platform_admin
--   - Regular end_user can access developer, global, agent (unchanged)
-- =============================================================================
DROP POLICY IF EXISTS packet_store_scope_access ON packet_store;
CREATE POLICY packet_store_scope_access ON packet_store
    FOR ALL
    USING (
        scope IS NULL
        OR scope IN ('developer', 'global', 'agent')
        OR (scope = 'cursor' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('cursor', 'cursor_user', 'platform_admin'))
        OR (scope = 'l-private' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('l9_system', 'platform_admin'))
    )
    WITH CHECK (
        scope IS NULL
        OR scope IN ('developer', 'global', 'agent')
        OR (scope = 'cursor' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('cursor', 'cursor_user', 'platform_admin'))
        OR (scope = 'l-private' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('l9_system', 'platform_admin'))
    );

-- =============================================================================
-- STEP 4: Fix semantic_memory scope policy (was stuck on 0008 defaults)
--   The 0008 policy only allowed scope IS NULL or 'shared' for end_user,
--   blocking all modern scopes (developer, global, agent, cursor).
--   This aligns semantic_memory with packet_store's scope model.
-- =============================================================================
DROP POLICY IF EXISTS semantic_memory_scope_access ON semantic_memory;
CREATE POLICY semantic_memory_scope_access ON semantic_memory
    FOR ALL
    USING (
        scope IS NULL
        OR scope IN ('developer', 'global', 'agent', 'shared')
        OR (scope = 'cursor' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('cursor', 'cursor_user', 'platform_admin'))
        OR (scope = 'l-private' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('l9_system', 'platform_admin'))
    )
    WITH CHECK (
        scope IS NULL
        OR scope IN ('developer', 'global', 'agent', 'shared')
        OR (scope = 'cursor' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('cursor', 'cursor_user', 'platform_admin'))
        OR (scope = 'l-private' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('l9_system', 'platform_admin'))
    );

-- Also fix knowledge_facts scope policy (same issue from 0008)
DROP POLICY IF EXISTS knowledge_facts_scope_access ON knowledge_facts;
CREATE POLICY knowledge_facts_scope_access ON knowledge_facts
    FOR ALL
    USING (
        scope IS NULL
        OR scope IN ('developer', 'global', 'agent', 'shared')
        OR (scope = 'cursor' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('cursor', 'cursor_user', 'platform_admin'))
        OR (scope = 'l-private' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('l9_system', 'platform_admin'))
    )
    WITH CHECK (
        scope IS NULL
        OR scope IN ('developer', 'global', 'agent', 'shared')
        OR (scope = 'cursor' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('cursor', 'cursor_user', 'platform_admin'))
        OR (scope = 'l-private' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('l9_system', 'platform_admin'))
    );

-- =============================================================================
-- STEP 5: Verification
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 0033 completed successfully';
    RAISE NOTICE '   - Added "cursor" scope to packet_store_scope_check constraint';
    RAISE NOTICE '   - Updated packet_store RLS: cursor scope requires app.role IN (cursor, cursor_user, platform_admin)';
    RAISE NOTICE '   - Fixed semantic_memory RLS: now allows developer, global, agent, cursor scopes';
    RAISE NOTICE '   - Fixed knowledge_facts RLS: same scope alignment';
    RAISE NOTICE '   - Valid scopes are now: developer, global, l-private, agent, cursor';
END $$;
