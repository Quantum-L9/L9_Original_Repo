-- =============================================================================
-- L9 Memory Substrate - Semantic Memory Scope/Project Index
-- Migration: 0030_semantic_memory_scope_project_index.sql
-- Version: 2.4.0
-- Date: 2026-02-11
-- =============================================================================
--
-- PURPOSE:
--   Improve semantic_memory query performance for governance-enforced predicates:
--   scope + payload.project_id + tenant/org/user + recency ordering.
--
-- SAFE:
--   - Idempotent (CREATE INDEX IF NOT EXISTS)
--   - No data rewrite
-- =============================================================================

BEGIN;

CREATE INDEX IF NOT EXISTS idx_semantic_scope_project_tenant_org_user_created
    ON semantic_memory (
        scope,
        ((payload->>'_project_id')),
        tenant_id,
        org_id,
        user_id,
        created_at DESC
    );

COMMIT;
