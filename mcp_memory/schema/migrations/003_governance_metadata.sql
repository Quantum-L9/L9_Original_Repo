-- Migration: 003_governance_metadata
-- Purpose: Add governance columns for L/C caller separation
-- See: mcp_memory/memory-setup-instructions.md for full spec
-- 
-- Invariants enforced:
-- - metadata.creator is ALWAYS set server-side ("L-CTO" or "Cursor-IDE")
-- - metadata.source is ALWAYS set server-side ("l9-kernel" or "cursor-ide")
-- - C can only UPDATE/DELETE rows where metadata->>'creator' = 'Cursor-IDE'
-- - All operations are captured in audit_log with caller details

-- =============================================================================
-- Add caller column to audit_log for governance trail
-- =============================================================================

ALTER TABLE memory.audit_log 
ADD COLUMN IF NOT EXISTS caller TEXT;

COMMENT ON COLUMN memory.audit_log.caller IS 
    'Caller identity: "L" (L-CTO kernel) or "C" (Cursor IDE). Determined from API key.';

-- =============================================================================
-- Create index for caller-based audit queries
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_audit_log_caller 
ON memory.audit_log(caller) 
WHERE caller IS NOT NULL;

-- =============================================================================
-- Create function to validate governance metadata on write
-- =============================================================================

CREATE OR REPLACE FUNCTION memory.validate_governance_metadata()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure metadata.creator is present
    IF NEW.metadata IS NULL OR NEW.metadata->>'creator' IS NULL THEN
        RAISE EXCEPTION 'metadata.creator is required (must be "L-CTO" or "Cursor-IDE")';
    END IF;
    
    -- Ensure metadata.source is present
    IF NEW.metadata->>'source' IS NULL THEN
        RAISE EXCEPTION 'metadata.source is required (must be "l9-kernel" or "cursor-ide")';
    END IF;
    
    -- Validate creator values
    IF NEW.metadata->>'creator' NOT IN ('L-CTO', 'Cursor-IDE', 'unknown') THEN
        RAISE EXCEPTION 'metadata.creator must be "L-CTO" or "Cursor-IDE", got: %', NEW.metadata->>'creator';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Add governance triggers to all memory tables
-- =============================================================================

DROP TRIGGER IF EXISTS trg_validate_governance_short_term ON memory.short_term;
CREATE TRIGGER trg_validate_governance_short_term
    BEFORE INSERT OR UPDATE ON memory.short_term
    FOR EACH ROW
    EXECUTE FUNCTION memory.validate_governance_metadata();

DROP TRIGGER IF EXISTS trg_validate_governance_medium_term ON memory.medium_term;
CREATE TRIGGER trg_validate_governance_medium_term
    BEFORE INSERT OR UPDATE ON memory.medium_term
    FOR EACH ROW
    EXECUTE FUNCTION memory.validate_governance_metadata();

DROP TRIGGER IF EXISTS trg_validate_governance_long_term ON memory.long_term;
CREATE TRIGGER trg_validate_governance_long_term
    BEFORE INSERT OR UPDATE ON memory.long_term
    FOR EACH ROW
    EXECUTE FUNCTION memory.validate_governance_metadata();

-- =============================================================================
-- Create view for easy governance auditing
-- =============================================================================

CREATE OR REPLACE VIEW memory.governance_audit AS
SELECT 
    id,
    operation,
    table_name,
    memory_id,
    user_id,
    caller,
    status,
    details->>'creator' AS creator,
    details->>'source' AS source,
    created_at
FROM memory.audit_log
WHERE details IS NOT NULL
ORDER BY created_at DESC;

COMMENT ON VIEW memory.governance_audit IS 
    'Governance audit view showing caller identity, creator, and source for all memory operations.';

-- =============================================================================
-- Analyze tables for query planner
-- =============================================================================

ANALYZE memory.audit_log;

