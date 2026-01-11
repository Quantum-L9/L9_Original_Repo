-- =============================================================================
-- Migration: 0013_mcp_audit_columns
-- Purpose: Add MCP audit columns to tool_audit_log for governance tracking
-- Date: 2026-01-09
-- =============================================================================
-- 
-- Adds caller and project_id to tool_audit_log for MCP memory server audit.
-- This replaces the deprecated memory.audit_log from mcp_memory/schema.
--
-- MCP server uses:
--   - packet_store for memory operation audit (save, search)
--   - tool_audit_log for MCP tool execution audit
--
-- Dependencies: 0011_tool_audit_log.sql must be applied first
-- =============================================================================

BEGIN;

-- Add caller column (L or C)
ALTER TABLE tool_audit_log 
ADD COLUMN IF NOT EXISTS caller TEXT;

COMMENT ON COLUMN tool_audit_log.caller IS 
    'Caller identity: "L" (L-CTO kernel) or "C" (Cursor IDE). Determined from API key.';

-- Add project_id column (for multi-project isolation)
ALTER TABLE tool_audit_log 
ADD COLUMN IF NOT EXISTS project_id TEXT;

COMMENT ON COLUMN tool_audit_log.project_id IS 
    'Project identifier: "l9" for L9 repo, NULL for global scope. Enables multi-project isolation.';

-- Create indexes for audit queries
CREATE INDEX IF NOT EXISTS idx_tool_audit_caller 
ON tool_audit_log(caller, timestamp DESC)
WHERE caller IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_tool_audit_project 
ON tool_audit_log(project_id, timestamp DESC)
WHERE project_id IS NOT NULL;

-- Create composite index for governance queries
CREATE INDEX IF NOT EXISTS idx_tool_audit_governance 
ON tool_audit_log(caller, project_id, timestamp DESC)
WHERE caller IS NOT NULL;

-- Analyze for query planner
ANALYZE tool_audit_log;

COMMIT;

-- =============================================================================
-- Usage Example:
-- =============================================================================
-- 
-- INSERT INTO tool_audit_log (
--     tool_name, agent_id, caller, project_id, 
--     input_data, output_data, duration_ms, timestamp
-- ) VALUES (
--     'save_memory',
--     'cursor',
--     'C',  -- Caller: Cursor IDE
--     'l9',  -- Project: L9 repo
--     '{"content": "...", "kind": "preference", "scope": "developer"}'::jsonb,
--     '{"packet_id": "...", "status": "success"}'::jsonb,
--     45.2,
--     NOW()
-- );
--
-- =============================================================================

