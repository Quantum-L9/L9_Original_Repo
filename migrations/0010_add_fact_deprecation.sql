-- =============================================================================
-- L9 Memory Substrate - Migration 0010
-- Version: 1.2.0
-- Purpose: Add deprecation columns to knowledge_facts for contradiction tracking
-- =============================================================================
-- Enables soft-deprecation of facts when contradictions are detected.
-- Supports the state layer's contradiction tracking responsibilities.
-- Apply AFTER 0005_init_knowledge_facts.sql
-- =============================================================================

-- Add deprecation columns to knowledge_facts
ALTER TABLE knowledge_facts
ADD COLUMN IF NOT EXISTS deprecated BOOLEAN DEFAULT FALSE;

ALTER TABLE knowledge_facts
ADD COLUMN IF NOT EXISTS deprecated_at TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE knowledge_facts
ADD COLUMN IF NOT EXISTS deprecated_reason TEXT;

ALTER TABLE knowledge_facts
ADD COLUMN IF NOT EXISTS contradiction_count INTEGER DEFAULT 0;

-- Index for finding active (non-deprecated) facts
CREATE INDEX IF NOT EXISTS idx_knowledge_facts_active
    ON knowledge_facts (subject, predicate)
    WHERE deprecated = FALSE;

-- Index for finding deprecated facts (for auditing)
CREATE INDEX IF NOT EXISTS idx_knowledge_facts_deprecated
    ON knowledge_facts (deprecated_at DESC)
    WHERE deprecated = TRUE;

-- =============================================================================
-- Comments
-- =============================================================================
COMMENT ON COLUMN knowledge_facts.deprecated IS 'Soft-delete flag for contradicted facts';
COMMENT ON COLUMN knowledge_facts.deprecated_at IS 'Timestamp when fact was deprecated';
COMMENT ON COLUMN knowledge_facts.deprecated_reason IS 'Reason for deprecation (contradiction, manual, etc.)';
COMMENT ON COLUMN knowledge_facts.contradiction_count IS 'Number of times this fact was contradicted';

-- =============================================================================
-- End Migration 0010
-- =============================================================================
