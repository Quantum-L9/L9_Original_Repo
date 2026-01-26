-- ============================================================================
-- L9 World Model Entities Table
-- Migration: 0004_init_world_model_entities.sql
-- Description: Creates persistent storage for world model entities
-- ============================================================================

-- Create world_model_entities table
CREATE TABLE IF NOT EXISTS world_model_entities (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL DEFAULT 'unknown',
    attributes JSONB NOT NULL DEFAULT '{}',
    confidence DOUBLE PRECISION DEFAULT 1.0,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    version INTEGER DEFAULT 1
);

-- Index for confidence-based queries (e.g., filtering low-confidence entities)
CREATE INDEX IF NOT EXISTS idx_wm_entities_confidence
    ON world_model_entities(confidence);

-- Index for type-based filtering
CREATE INDEX IF NOT EXISTS idx_wm_entities_type
    ON world_model_entities(entity_type);

-- Index for temporal queries
CREATE INDEX IF NOT EXISTS idx_wm_entities_updated
    ON world_model_entities(updated_at DESC);

-- GIN index for JSONB attribute queries
CREATE INDEX IF NOT EXISTS idx_wm_entities_attributes
    ON world_model_entities USING GIN (attributes);

-- Comments
COMMENT ON TABLE world_model_entities IS 'Persistent storage for L9 World Model entities';
COMMENT ON COLUMN world_model_entities.entity_id IS 'Unique identifier for the entity';
COMMENT ON COLUMN world_model_entities.entity_type IS 'Type classification of the entity';
COMMENT ON COLUMN world_model_entities.attributes IS 'JSONB attributes and properties';
COMMENT ON COLUMN world_model_entities.confidence IS 'Confidence score (0.0 to 1.0)';
COMMENT ON COLUMN world_model_entities.version IS 'Version number for optimistic locking';
