-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Migration: 0028_optimize_vector_indexing.sql
-- Purpose: Add IVFFlat index for production-scale pgvector search
-- Author: L9 Engineering (GMP Phase 0)
-- Date: 2026-01-29
-- Risk: T2 (online index creation, reversible)
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- Rationale:
-- The existing HNSW index (0001_init_memory_substrate.sql) works well for
-- small-to-medium datasets (<100K vectors). IVFFlat provides better
-- performance at scale (>100K vectors) with tunable accuracy/speed tradeoffs.
-- Both indexes can coexist; the query planner selects the optimal one.

-- Dependency check: Ensure pgvector extension exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'vector'
    ) THEN
        RAISE EXCEPTION 'pgvector extension not found. Run 0001_init_memory_substrate.sql first.';
    END IF;
END $$;

-- Create IVFFlat index on packet_store.embedding column
-- Configuration:
-- - lists=100: Number of clusters (adjust based on dataset size)
--   Rule of thumb: sqrt(total_rows) or rows/1000
-- - cosine distance: Matches HNSW index for query compatibility
-- - CONCURRENTLY: Allows online index creation without blocking writes
--   (requires PostgreSQL 11+)

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_packet_store_embedding_ivfflat
ON packet_store
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Performance note:
-- After adding significant data (>10K new vectors), run:
--   REINDEX INDEX CONCURRENTLY idx_packet_store_embedding_ivfflat;
-- to rebalance clusters for optimal search performance.

-- Query pattern (reuses existing application code):
-- SELECT * FROM packet_store
-- ORDER BY embedding <=> '[1536-dim vector]'::vector
-- LIMIT 10;
-- Query planner automatically selects IVFFlat or HNSW based on statistics.

-- Rollback:
-- DROP INDEX CONCURRENTLY IF EXISTS idx_packet_store_embedding_ivfflat;
