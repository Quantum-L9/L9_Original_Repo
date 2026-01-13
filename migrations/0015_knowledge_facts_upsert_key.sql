-- =============================================================================
-- L9 Memory Substrate - Migration 0015
-- Version: 2.1.0
-- Purpose: Add unique index for knowledge_facts UPSERT (GMP-67 unified pipeline)
-- =============================================================================
-- Enables idempotent fact insertion via ON CONFLICT.
-- Same packet enriched multiple times will not create duplicate facts.
-- Apply AFTER 0010_add_fact_deprecation.sql
-- =============================================================================

-- Unique index for UPSERT on (source_packet, subject, predicate)
-- Only applies when source_packet IS NOT NULL (orphan facts excluded)
CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_facts_upsert_key
    ON knowledge_facts (source_packet, subject, predicate)
    WHERE source_packet IS NOT NULL;

-- =============================================================================
-- Comments
-- =============================================================================
COMMENT ON INDEX idx_knowledge_facts_upsert_key IS 
    'Enables idempotent UPSERT: same packet enriched twice = no duplicates (GMP-67)';

-- =============================================================================
-- End Migration 0015
-- =============================================================================
