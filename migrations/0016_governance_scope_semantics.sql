-- =============================================================================
-- L9 Memory Substrate - Governance Hardening: Scope Semantics
-- Migration: 0016_governance_scope_semantics.sql
-- Version: 2.2.0
-- Date: 2026-01-14
-- =============================================================================
--
-- PURPOSE: Memory Governance Hardening - Phase 0
--   - Preserve scope semantics: developer / global / l-private
--   - Do NOT collapse developer/global to 'shared'
--   - Add CHECK constraint for valid scope values
--   - Backfill existing 'shared' scope based on metadata
--
-- GOVERNANCE INVARIANT: Scope semantics must be preserved in DB
-- =============================================================================

BEGIN;

-- =============================================================================
-- STEP 1: Remove existing scope CHECK constraint if any
-- =============================================================================
ALTER TABLE packet_store
  DROP CONSTRAINT IF EXISTS packet_store_scope_check;

-- =============================================================================
-- STEP 2: Add new CHECK constraint with all valid scope values
-- Note: 'shared' kept temporarily for backward compatibility during migration
-- =============================================================================
ALTER TABLE packet_store
  ADD CONSTRAINT packet_store_scope_check
  CHECK (scope IN ('developer', 'global', 'l-private', 'shared', 'cursor'));

-- =============================================================================
-- STEP 3: Backfill existing 'shared' scope based on metadata
-- Logic:
--   - If metadata.creator = 'L-CTO' -> l-private
--   - If metadata.caller = 'C' (Cursor) -> developer
--   - Else -> global
-- =============================================================================
UPDATE packet_store
SET scope = CASE
  WHEN envelope->'metadata'->>'creator' = 'L-CTO' THEN 'l-private'
  WHEN envelope->'metadata'->>'caller' = 'C' THEN 'developer'
  WHEN envelope->'metadata'->>'caller_id' = 'C' THEN 'developer'
  ELSE 'global'
END
WHERE scope = 'shared';

-- =============================================================================
-- STEP 4: Backfill 'cursor' scope to 'developer' for consistency
-- The old 'cursor' scope is now 'developer'
-- =============================================================================
UPDATE packet_store
SET scope = 'developer'
WHERE scope = 'cursor';

-- =============================================================================
-- STEP 5: Create index on scope for efficient filtering
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_packet_scope_governance
  ON packet_store(scope, timestamp DESC);

-- =============================================================================
-- STEP 6: Update RLS policy for new scope values
-- =============================================================================
DROP POLICY IF EXISTS packet_store_scope_access ON packet_store;
CREATE POLICY packet_store_scope_access ON packet_store
    FOR ALL
    USING (
        scope IS NULL
        OR scope IN ('shared', 'developer', 'global')
        OR (scope = 'l-private' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('l9_system', 'platform_admin'))
    )
    WITH CHECK (
        scope IS NULL
        OR scope IN ('shared', 'developer', 'global')
        OR (scope = 'l-private' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('l9_system', 'platform_admin'))
    );

-- =============================================================================
-- STEP 7: Verify backfill completed successfully
-- =============================================================================
DO $$
DECLARE
    shared_count INT;
    cursor_count INT;
    developer_count INT;
    global_count INT;
    l_private_count INT;
BEGIN
    SELECT COUNT(*) INTO shared_count FROM packet_store WHERE scope = 'shared';
    SELECT COUNT(*) INTO cursor_count FROM packet_store WHERE scope = 'cursor';
    SELECT COUNT(*) INTO developer_count FROM packet_store WHERE scope = 'developer';
    SELECT COUNT(*) INTO global_count FROM packet_store WHERE scope = 'global';
    SELECT COUNT(*) INTO l_private_count FROM packet_store WHERE scope = 'l-private';

    RAISE NOTICE '=== Migration 0016 Scope Semantics - Pre-Finalize ===';
    RAISE NOTICE 'Remaining shared: % (should be 0)', shared_count;
    RAISE NOTICE 'Remaining cursor: % (should be 0)', cursor_count;
    RAISE NOTICE 'developer: %', developer_count;
    RAISE NOTICE 'global: %', global_count;
    RAISE NOTICE 'l-private: %', l_private_count;

    IF shared_count > 0 OR cursor_count > 0 THEN
        RAISE EXCEPTION 'Backfill incomplete: % shared and % cursor rows remain. Cannot finalize CHECK constraint.', shared_count, cursor_count;
    END IF;
END
$$;

-- =============================================================================
-- STEP 8: POST-BACKFILL - Remove 'shared' and 'cursor' from CHECK constraint
-- GOVERNANCE FIX: After backfill, these legacy values should no longer be allowed
-- =============================================================================
ALTER TABLE packet_store
  DROP CONSTRAINT IF EXISTS packet_store_scope_check;

ALTER TABLE packet_store
  ADD CONSTRAINT packet_store_scope_check
  CHECK (scope IN ('developer', 'global', 'l-private'));

-- Update RLS policy to remove 'shared' reference
DROP POLICY IF EXISTS packet_store_scope_access ON packet_store;
CREATE POLICY packet_store_scope_access ON packet_store
    FOR ALL
    USING (
        scope IS NULL
        OR scope IN ('developer', 'global')
        OR (scope = 'l-private' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('l9_system', 'platform_admin'))
    )
    WITH CHECK (
        scope IS NULL
        OR scope IN ('developer', 'global')
        OR (scope = 'l-private' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('l9_system', 'platform_admin'))
    );

-- =============================================================================
-- STEP 9: Final verification
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 0016 completed successfully';
    RAISE NOTICE '   - Scope semantics preserved: developer, global, l-private';
    RAISE NOTICE '   - Legacy scopes (shared, cursor) removed from CHECK constraint';
    RAISE NOTICE '   - New packets can only use: developer, global, l-private';
END
$$;

COMMIT;

-- =============================================================================
-- END MIGRATION 0016
-- =============================================================================
