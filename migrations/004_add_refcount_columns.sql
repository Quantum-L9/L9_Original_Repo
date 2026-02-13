-- Migration: Add Reference Counting Support for TTL Safety
-- Version: 004
-- Date: 2026-02-12
-- Description: Adds metadata column and audit table for reference counting

-- Add metadata column to packetstore for soft expiration tracking
ALTER TABLE packetstore
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Create index on soft_expired flag for efficient querying
CREATE INDEX IF NOT EXISTS idx_packet_soft_expired
ON packetstore ((metadata->>'soft_expired'))
WHERE metadata->>'soft_expired' = 'true';

-- Create index on metadata for general queries
CREATE INDEX IF NOT EXISTS idx_packet_metadata
ON packetstore USING GIN (metadata);

-- Create audit table for reference count tracking (optional, for debugging)
CREATE TABLE IF NOT EXISTS packet_refcount_audit (
    packet_id TEXT PRIMARY KEY,
    lineage_refs INT DEFAULT 0,
    fact_refs INT DEFAULT 0,
    checkpoint_refs INT DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW(),
    last_checked_by TEXT,  -- Which process computed the refcount
    CONSTRAINT fk_packet
        FOREIGN KEY(packet_id)
        REFERENCES packetstore(packetid)
        ON DELETE CASCADE
);

-- Create index for finding packets with high refcounts
CREATE INDEX IF NOT EXISTS idx_refcount_total
ON packet_refcount_audit ((lineage_refs + fact_refs + checkpoint_refs));

-- Create function to update refcount audit timestamp
CREATE OR REPLACE FUNCTION update_refcount_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic timestamp updates
DROP TRIGGER IF EXISTS trigger_refcount_timestamp ON packet_refcount_audit;
CREATE TRIGGER trigger_refcount_timestamp
    BEFORE UPDATE ON packet_refcount_audit
    FOR EACH ROW
    EXECUTE FUNCTION update_refcount_timestamp();

-- Add comment explaining the schema
COMMENT ON TABLE packet_refcount_audit IS
'Tracks reference counts for packets to prevent premature TTL-based deletion. Updated by ReferenceCountingService.';

COMMENT ON COLUMN packetstore.metadata IS
'JSONB metadata including soft_expired flag, custom tags, and other extensible properties.';

-- Migration complete
SELECT 'Migration 004 completed successfully' AS status;
