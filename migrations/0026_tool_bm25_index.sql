-- Migration: 0026_tool_bm25_index.sql
-- GMP-TD-WIRE: Add BM25 full-text search to tool_embeddings
-- Created: 2026-01-25
--
-- Purpose: Enable hybrid search (semantic + keyword) for tool discovery
-- Pattern: Harvested from Tool Discovery research

-- Add tsvector column for pre-computed full-text search
ALTER TABLE tool_embeddings
ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- Populate search_vector from description
UPDATE tool_embeddings
SET search_vector = to_tsvector('english', COALESCE(description, ''));

-- Create GIN index for fast full-text search
CREATE INDEX IF NOT EXISTS idx_tool_embeddings_search_vector
    ON tool_embeddings
    USING gin (search_vector);

-- Trigger to auto-update search_vector on insert/update
CREATE OR REPLACE FUNCTION update_tool_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector = to_tsvector('english', COALESCE(NEW.description, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_tool_search_vector ON tool_embeddings;
CREATE TRIGGER trigger_tool_search_vector
    BEFORE INSERT OR UPDATE OF description ON tool_embeddings
    FOR EACH ROW
    EXECUTE FUNCTION update_tool_search_vector();

-- Comment for documentation
COMMENT ON COLUMN tool_embeddings.search_vector IS 'GMP-TD-WIRE: Pre-computed tsvector for BM25 full-text search';
