-- =============================================================================
-- L9 Memory Substrate - Migration 0022
-- Version: 3.2.0
-- Purpose: Add temporal validity columns for time-travel queries
-- =============================================================================
-- Enables querying "what facts were valid at time T" vs "what facts are valid now".
-- Supports fact versioning, supersession tracking, and temporal debugging.
-- Apply AFTER 0021_gmp_learning.sql
-- =============================================================================

-- =============================================================================
-- ALTER TABLE: semantic_facts - Add temporal validity columns
-- =============================================================================

-- valid_from: When this fact became valid (defaults to created_at)
ALTER TABLE semantic_facts
ADD COLUMN IF NOT EXISTS valid_from TIMESTAMP WITH TIME ZONE;

-- valid_to: When this fact stopped being valid (NULL = still valid)
ALTER TABLE semantic_facts
ADD COLUMN IF NOT EXISTS valid_to TIMESTAMP WITH TIME ZONE;

-- superseded_by: Reference to the fact that replaced this one
ALTER TABLE semantic_facts
ADD COLUMN IF NOT EXISTS superseded_by UUID REFERENCES semantic_facts(fact_id);

-- =============================================================================
-- BACKFILL: Set valid_from to created_at for existing rows
-- =============================================================================
UPDATE semantic_facts
SET valid_from = created_at
WHERE valid_from IS NULL;

-- =============================================================================
-- INDEXES for temporal queries
-- =============================================================================

-- Index for point-in-time queries: "What was valid at time T?"
CREATE INDEX IF NOT EXISTS idx_semantic_facts_temporal_validity
    ON semantic_facts (valid_from, valid_to)
    WHERE valid_to IS NOT NULL OR valid_from IS NOT NULL;

-- Index for currently valid facts
CREATE INDEX IF NOT EXISTS idx_semantic_facts_currently_valid
    ON semantic_facts (tenant_id, tier)
    WHERE valid_to IS NULL;

-- Index for supersession chain
CREATE INDEX IF NOT EXISTS idx_semantic_facts_superseded_by
    ON semantic_facts (superseded_by)
    WHERE superseded_by IS NOT NULL;

-- =============================================================================
-- FUNCTION: Check if fact was valid at a point in time
-- =============================================================================
CREATE OR REPLACE FUNCTION is_fact_valid_at(
    p_fact_id UUID,
    p_point_in_time TIMESTAMP WITH TIME ZONE
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM semantic_facts
        WHERE fact_id = p_fact_id
        AND valid_from <= p_point_in_time
        AND (valid_to IS NULL OR valid_to > p_point_in_time)
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- =============================================================================
-- Comments
-- =============================================================================
COMMENT ON COLUMN semantic_facts.valid_from IS 'When this fact became valid (temporal lower bound)';
COMMENT ON COLUMN semantic_facts.valid_to IS 'When this fact stopped being valid (NULL = currently valid)';
COMMENT ON COLUMN semantic_facts.superseded_by IS 'Reference to fact that replaced this one (version chain)';
COMMENT ON FUNCTION is_fact_valid_at(UUID, TIMESTAMP WITH TIME ZONE) IS 'Check if a fact was valid at a specific point in time';

-- =============================================================================
-- End Migration 0022
-- =============================================================================
