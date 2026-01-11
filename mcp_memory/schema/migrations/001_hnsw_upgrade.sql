-- Migration: Upgrade IVFFlat indexes to HNSW
-- Run this on existing deployments

-- Drop old IVFFlat indexes
DROP INDEX IF EXISTS memory.idx_short_term_embedding;
DROP INDEX IF EXISTS memory.idx_medium_term_embedding;
DROP INDEX IF EXISTS memory.idx_long_term_embedding;

-- Create new HNSW indexes
CREATE INDEX idx_short_term_embedding ON memory.short_term USING hnsw(embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_medium_term_embedding ON memory.medium_term USING hnsw(embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_long_term_embedding ON memory.long_term USING hnsw(embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Analyze tables for query planner
ANALYZE memory.short_term;
ANALYZE memory.medium_term;
ANALYZE memory.long_term;
