-- Migration: 0025_tool_embeddings.sql
-- GMP-78: Semantic Tool Retrieval (Tool RAG)
-- Created: 2026-01-15
--
-- Purpose: Store tool embeddings for semantic search over tool definitions.
-- This enables RAG-based tool retrieval so agents receive only relevant tools.

-- Tool embeddings table for semantic search
CREATE TABLE IF NOT EXISTS tool_embeddings (
    tool_name VARCHAR(255) PRIMARY KEY,
    description TEXT NOT NULL,
    category VARCHAR(64),
    embedding vector(1536),  -- OpenAI text-embedding-3-small dimension
    negative_constraints TEXT[],  -- Array of "don't use when X" guidance strings
    metadata JSONB DEFAULT '{}',  -- Additional tool metadata (risk_level, scope, etc.)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for vector similarity search (cosine distance)
-- Using ivfflat with 20 lists - appropriate for ~100-200 tools
CREATE INDEX IF NOT EXISTS idx_tool_embeddings_vector
    ON tool_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 20);

-- Index for category filtering
CREATE INDEX IF NOT EXISTS idx_tool_embeddings_category
    ON tool_embeddings (category);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_tool_embeddings_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for auto-updating timestamp
DROP TRIGGER IF EXISTS trigger_tool_embeddings_updated ON tool_embeddings;
CREATE TRIGGER trigger_tool_embeddings_updated
    BEFORE UPDATE ON tool_embeddings
    FOR EACH ROW
    EXECUTE FUNCTION update_tool_embeddings_timestamp();

-- Comment for documentation
COMMENT ON TABLE tool_embeddings IS 'GMP-78: Tool embeddings for semantic tool retrieval (RAG for tools)';
COMMENT ON COLUMN tool_embeddings.embedding IS 'OpenAI text-embedding-3-small vector (1536 dimensions)';
COMMENT ON COLUMN tool_embeddings.negative_constraints IS 'Array of guidance strings for when NOT to use this tool';
