-- Migration: 004_audit_project_id
-- Purpose: Add project_id column to audit_log for Perplexity integration
-- See: mcp_memory/PERPLEXITY_INTEGRATION.md
-- 
-- Perplexity recommendation: Log all Cursor calls with project_id for multi-project isolation

-- =============================================================================
-- Add project_id column to audit_log
-- =============================================================================

ALTER TABLE memory.audit_log 
ADD COLUMN IF NOT EXISTS project_id TEXT;

COMMENT ON COLUMN memory.audit_log.project_id IS 
    'Project identifier: "l9" for L9 repo, NULL for global scope. Enables multi-project isolation.';

-- =============================================================================
-- Create index for project-based audit queries
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_audit_log_project 
ON memory.audit_log(project_id, created_at DESC)
WHERE project_id IS NOT NULL;

-- =============================================================================
-- Update governance_audit view to include project_id
-- =============================================================================

CREATE OR REPLACE VIEW memory.governance_audit AS
SELECT 
    id,
    operation,
    table_name,
    memory_id,
    user_id,
    caller,
    project_id,
    status,
    details->>'creator' AS creator,
    details->>'source' AS source,
    created_at
FROM memory.audit_log
WHERE details IS NOT NULL
ORDER BY created_at DESC;

COMMENT ON VIEW memory.governance_audit IS 
    'Governance audit view showing caller identity, creator, source, and project_id for all memory operations.';

-- =============================================================================
-- Analyze tables for query planner
-- =============================================================================

ANALYZE memory.audit_log;

