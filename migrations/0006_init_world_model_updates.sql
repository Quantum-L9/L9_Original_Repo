-- ============================================================================
-- L9 World Model Updates Table
-- Migration: 0005_init_world_model_updates.sql
-- Description: Tracks all updates applied to the world model from insights
-- ============================================================================

-- Create world_model_updates table
CREATE TABLE IF NOT EXISTS world_model_updates (
    update_id UUID PRIMARY KEY,
    insight_id UUID,
    insight_type TEXT,
    entities JSONB,
    content JSONB,
    confidence DOUBLE PRECISION,
    applied_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    source_packet UUID,
    state_version_before INTEGER,
    state_version_after INTEGER
);

-- Index for confidence filtering
CREATE INDEX IF NOT EXISTS idx_wm_updates_confidence
    ON world_model_updates(confidence);

-- Index for insight type filtering
CREATE INDEX IF NOT EXISTS idx_wm_updates_insight_type
    ON world_model_updates(insight_type);

-- Index for temporal queries
CREATE INDEX IF NOT EXISTS idx_wm_updates_applied
    ON world_model_updates(applied_at DESC);

-- Index for linking back to insights
CREATE INDEX IF NOT EXISTS idx_wm_updates_insight
    ON world_model_updates(insight_id);

-- GIN index for entity array queries
CREATE INDEX IF NOT EXISTS idx_wm_updates_entities
    ON world_model_updates USING GIN (entities);

-- Comments
COMMENT ON TABLE world_model_updates IS 'Audit log of all world model updates from insights';
COMMENT ON COLUMN world_model_updates.update_id IS 'Unique identifier for this update';
COMMENT ON COLUMN world_model_updates.insight_id IS 'Source insight that triggered this update';
COMMENT ON COLUMN world_model_updates.insight_type IS 'Type of insight (pattern, conclusion, etc.)';
COMMENT ON COLUMN world_model_updates.entities IS 'Array of entity IDs affected';
COMMENT ON COLUMN world_model_updates.content IS 'Update content/payload';
COMMENT ON COLUMN world_model_updates.confidence IS 'Confidence score of the update';
COMMENT ON COLUMN world_model_updates.state_version_before IS 'World model version before update';
COMMENT ON COLUMN world_model_updates.state_version_after IS 'World model version after update';
