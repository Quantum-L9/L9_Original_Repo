-- Migration: 10x Memory Substrate Upgrade for Cursor
-- Adds confidence scoring, relationships, and enhanced temporal queries
-- Run this on existing deployments AFTER 001_hnsw_upgrade.sql

-- =============================================================================
-- Add confidence and source tracking to long_term memories
-- =============================================================================

-- Add confidence column (how sure are we about this memory)
ALTER TABLE memory.long_term 
ADD COLUMN IF NOT EXISTS confidence FLOAT DEFAULT 1.0 
CHECK (confidence >= 0.0 AND confidence <= 1.0);

-- Add source column (where did this memory come from)
ALTER TABLE memory.long_term 
ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'cursor';

-- Add session_id for session-based grouping
ALTER TABLE memory.long_term 
ADD COLUMN IF NOT EXISTS session_id TEXT;

-- =============================================================================
-- Memory relationships table (for linking related memories)
-- =============================================================================

CREATE TABLE IF NOT EXISTS memory.memory_relationships (
    id BIGSERIAL PRIMARY KEY,
    source_memory_id BIGINT NOT NULL REFERENCES memory.long_term(id) ON DELETE CASCADE,
    target_memory_id BIGINT NOT NULL REFERENCES memory.long_term(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL DEFAULT 'related',
    strength FLOAT DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_relationship_type CHECK (
        relationship_type IN ('related', 'supersedes', 'contradicts', 'elaborates', 'derived_from')
    ),
    CONSTRAINT check_no_self_reference CHECK (source_memory_id != target_memory_id),
    UNIQUE(source_memory_id, target_memory_id, relationship_type)
);

CREATE INDEX idx_relationships_source ON memory.memory_relationships(source_memory_id);
CREATE INDEX idx_relationships_target ON memory.memory_relationships(target_memory_id);

-- =============================================================================
-- Session summaries table (for cross-session learning)
-- =============================================================================

CREATE TABLE IF NOT EXISTS memory.session_summaries (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL UNIQUE,
    summary TEXT NOT NULL,
    key_decisions TEXT[] DEFAULT '{}',
    errors_encountered TEXT[] DEFAULT '{}',
    successes TEXT[] DEFAULT '{}',
    memory_ids BIGINT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    duration_minutes INT
);

CREATE INDEX idx_session_user ON memory.session_summaries(user_id, created_at DESC);

-- =============================================================================
-- Enhanced indexes for temporal queries
-- =============================================================================

-- Index for temporal queries (created_at range queries)
CREATE INDEX IF NOT EXISTS idx_long_term_temporal 
ON memory.long_term(user_id, created_at DESC, updated_at DESC);

-- Index for confidence-based retrieval
CREATE INDEX IF NOT EXISTS idx_long_term_confidence 
ON memory.long_term(user_id, confidence DESC) 
WHERE confidence >= 0.7;

-- Index for session-based queries
CREATE INDEX IF NOT EXISTS idx_long_term_session 
ON memory.long_term(session_id, created_at DESC) 
WHERE session_id IS NOT NULL;

-- =============================================================================
-- Enhanced stats view with confidence metrics
-- =============================================================================

CREATE OR REPLACE VIEW memory.enhanced_stats_view AS
SELECT 
    'long_term' as memory_type,
    COUNT(*) as total_count,
    COUNT(DISTINCT user_id) as unique_users,
    AVG(importance) as avg_importance,
    AVG(confidence) as avg_confidence,
    COUNT(*) FILTER (WHERE confidence >= 0.9) as high_confidence_count,
    COUNT(*) FILTER (WHERE confidence < 0.7) as low_confidence_count,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as last_24h_count,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') as last_7d_count,
    NOW() as calculated_at
FROM memory.long_term;

-- =============================================================================
-- Analyze tables for query planner
-- =============================================================================

ANALYZE memory.long_term;
ANALYZE memory.memory_relationships;
ANALYZE memory.session_summaries;

