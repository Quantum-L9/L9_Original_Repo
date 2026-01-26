-- =============================================================================
-- L9 Memory Substrate - Migration 0002
-- Version: 1.1.0
-- Purpose: Extend packet_store for threading, lineage, tags, and TTL
-- =============================================================================
-- IMPORTANT: Strictly additive - does NOT drop or rename columns.
-- All new columns are nullable or have defaults for backwards compatibility.
-- Apply AFTER 0001_init_memory_substrate.sql
-- =============================================================================

-- Add thread_id for conversation/session threading
ALTER TABLE packet_store
    ADD COLUMN IF NOT EXISTS thread_id UUID NULL;

-- Add parent_ids for packet lineage (array of UUIDs)
ALTER TABLE packet_store
    ADD COLUMN IF NOT EXISTS parent_ids UUID[] DEFAULT '{}';

-- Add tags for flexible categorization
ALTER TABLE packet_store
    ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';

-- Add TTL for temporal expiration
ALTER TABLE packet_store
    ADD COLUMN IF NOT EXISTS ttl TIMESTAMP WITHOUT TIME ZONE NULL;

-- Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_packet_thread
    ON packet_store (thread_id);

CREATE INDEX IF NOT EXISTS idx_packet_lineage
    ON packet_store USING GIN (parent_ids);

CREATE INDEX IF NOT EXISTS idx_packet_tags
    ON packet_store USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_packet_ttl
    ON packet_store (ttl)
    WHERE ttl IS NOT NULL;

-- =============================================================================
-- Comments
-- =============================================================================
COMMENT ON COLUMN packet_store.thread_id IS 'UUID linking packets in a conversation/session thread';
COMMENT ON COLUMN packet_store.parent_ids IS 'Array of parent packet UUIDs for lineage tracking';
COMMENT ON COLUMN packet_store.tags IS 'Flexible text tags for categorization and filtering';
COMMENT ON COLUMN packet_store.ttl IS 'Optional expiration timestamp for memory hygiene';

-- =============================================================================
-- End Migration 0002
-- =============================================================================
