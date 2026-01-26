-- ============================================================================
-- L9 World Model Snapshots Table
-- Migration: 0006_init_world_model_snapshots.sql
-- Description: Stores point-in-time snapshots of the entire world model
-- ============================================================================

-- Create world_model_snapshots table
CREATE TABLE IF NOT EXISTS world_model_snapshots (
    snapshot_id UUID PRIMARY KEY,
    snapshot JSONB NOT NULL,
    state_version INTEGER NOT NULL,
    entity_count INTEGER DEFAULT 0,
    relation_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    description TEXT,
    created_by TEXT DEFAULT 'system'
);

-- Index for temporal queries
CREATE INDEX IF NOT EXISTS idx_wm_snapshots_created
    ON world_model_snapshots(created_at DESC);

-- Index for version-based retrieval
CREATE INDEX IF NOT EXISTS idx_wm_snapshots_version
    ON world_model_snapshots(state_version DESC);

-- Comments
COMMENT ON TABLE world_model_snapshots IS 'Point-in-time snapshots of the L9 World Model state';
COMMENT ON COLUMN world_model_snapshots.snapshot_id IS 'Unique identifier for this snapshot';
COMMENT ON COLUMN world_model_snapshots.snapshot IS 'Full JSONB serialization of world model state';
COMMENT ON COLUMN world_model_snapshots.state_version IS 'World model version at snapshot time';
COMMENT ON COLUMN world_model_snapshots.entity_count IS 'Number of entities at snapshot time';
COMMENT ON COLUMN world_model_snapshots.relation_count IS 'Number of relations at snapshot time';
COMMENT ON COLUMN world_model_snapshots.description IS 'Optional description or reason for snapshot';
COMMENT ON COLUMN world_model_snapshots.created_by IS 'System or user that created the snapshot';
