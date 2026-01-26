-- =============================================================================
-- L9 Memory Substrate - Migration 0004
-- Version: 1.1.0+
-- Purpose: Create knowledge_facts table for extracted insights
-- =============================================================================
-- Stores subject-predicate-object triples extracted from packet processing.
-- Supports world model updates and knowledge graph integration.
-- Apply AFTER 0002_enhance_packet_store.sql
-- =============================================================================

-- =============================================================================
-- TABLE: knowledge_facts
-- Type: structured
-- Purpose: Store extracted knowledge facts (SPO triples) for world model
-- =============================================================================
CREATE TABLE IF NOT EXISTS knowledge_facts (
    fact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object JSONB NOT NULL,
    confidence DOUBLE PRECISION DEFAULT 0.8,
    source_packet UUID REFERENCES packet_store(packet_id) ON DELETE SET NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_knowledge_facts_subject
    ON knowledge_facts (subject);

CREATE INDEX IF NOT EXISTS idx_knowledge_facts_predicate
    ON knowledge_facts (predicate);

CREATE INDEX IF NOT EXISTS idx_knowledge_facts_source_packet
    ON knowledge_facts (source_packet)
    WHERE source_packet IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_knowledge_facts_created_at
    ON knowledge_facts (created_at DESC);

-- GIN index for JSONB object search
CREATE INDEX IF NOT EXISTS idx_knowledge_facts_object
    ON knowledge_facts USING GIN (object);

-- Composite index for subject-predicate lookups
CREATE INDEX IF NOT EXISTS idx_knowledge_facts_subject_predicate
    ON knowledge_facts (subject, predicate);

-- =============================================================================
-- Comments
-- =============================================================================
COMMENT ON TABLE knowledge_facts IS 'Extracted knowledge facts (SPO triples) for world model integration';
COMMENT ON COLUMN knowledge_facts.subject IS 'Entity or concept being described';
COMMENT ON COLUMN knowledge_facts.predicate IS 'Relationship or attribute type';
COMMENT ON COLUMN knowledge_facts.object IS 'Value, entity, or structured data as JSONB';
COMMENT ON COLUMN knowledge_facts.confidence IS 'Extraction confidence score (0.0-1.0)';
COMMENT ON COLUMN knowledge_facts.source_packet IS 'Reference to originating packet';

-- =============================================================================
-- End Migration 0004
-- =============================================================================
