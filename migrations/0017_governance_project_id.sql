-- =============================================================================
-- L9 Memory Substrate - Governance Hardening: Project ID Isolation
-- Migration: 0017_governance_project_id.sql
-- Version: 2.2.0
-- Date: 2026-01-14
-- =============================================================================
--
-- PURPOSE: Memory Governance Hardening - Phase 0
--   - Enforce project_id isolation at SQL level
--   - Backfill missing project_id with default 'l9'
--   - Add NOT NULL constraint after backfill
--
-- GOVERNANCE INVARIANT: Project isolation must be enforced at DB level
-- =============================================================================

BEGIN;

-- =============================================================================
-- STEP 1: Backfill missing project_id with default 'l9'
-- Uses jsonb_set to add project_id to envelope.metadata if missing
-- =============================================================================
UPDATE packet_store
SET envelope = jsonb_set(
    COALESCE(envelope, '{}'::jsonb),
    '{metadata,project_id}',
    '"l9"',
    true
)
WHERE envelope->'metadata'->>'project_id' IS NULL
   OR envelope->'metadata' IS NULL;

-- =============================================================================
-- STEP 2: Create index on project_id for efficient filtering
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_packet_project_id 
  ON packet_store((envelope->'metadata'->>'project_id'));

-- Combined index for scope + project_id queries
CREATE INDEX IF NOT EXISTS idx_packet_scope_project 
  ON packet_store(scope, (envelope->'metadata'->>'project_id'));

-- =============================================================================
-- STEP 3: Add NOT NULL constraint via CHECK (JSONB doesn't support direct NOT NULL)
-- This prevents new packets without project_id
-- =============================================================================
ALTER TABLE packet_store 
  DROP CONSTRAINT IF EXISTS packet_store_project_id_not_null;

ALTER TABLE packet_store 
  ADD CONSTRAINT packet_store_project_id_not_null 
  CHECK (envelope->'metadata'->>'project_id' IS NOT NULL);

-- =============================================================================
-- STEP 4: Verify migration
-- =============================================================================
DO $$
DECLARE
    null_project_count INT;
    l9_project_count INT;
    total_count INT;
BEGIN
    SELECT COUNT(*) INTO null_project_count 
    FROM packet_store 
    WHERE envelope->'metadata'->>'project_id' IS NULL;
    
    SELECT COUNT(*) INTO l9_project_count 
    FROM packet_store 
    WHERE envelope->'metadata'->>'project_id' = 'l9';
    
    SELECT COUNT(*) INTO total_count FROM packet_store;
    
    RAISE NOTICE '=== Migration 0017 Project ID Isolation ===';
    RAISE NOTICE 'Total packets: %', total_count;
    RAISE NOTICE 'Packets with project_id=l9: %', l9_project_count;
    RAISE NOTICE 'Packets with NULL project_id: % (should be 0)', null_project_count;
    
    IF null_project_count = 0 THEN
        RAISE NOTICE '✅ Migration 0017 completed successfully';
        RAISE NOTICE '   - All packets have project_id';
        RAISE NOTICE '   - NOT NULL constraint enforced';
    ELSE
        RAISE WARNING '⚠️ Migration 0017 failed - % packets still have NULL project_id', null_project_count;
    END IF;
END
$$;

COMMIT;

-- =============================================================================
-- END MIGRATION 0017
-- =============================================================================
