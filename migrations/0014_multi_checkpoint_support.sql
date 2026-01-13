-- Migration: 0014_multi_checkpoint_support
-- Version: 1.0.0
-- Purpose: Enable multi-checkpoint storage per agent for retention policies
--
-- Background:
--   Migration 0001 created graph_checkpoints with UNIQUE(agent_id),
--   limiting storage to ONE checkpoint per agent. This prevents retention
--   policies (keep_last_n, daily/weekly/monthly backups).
--
-- Changes:
--   1. Drop UNIQUE constraint on agent_id
--   2. Add 'reason' column (on_agent_shutdown, on_session_boundary, etc.)
--   3. Add 'checkpoint_number' for ordering within agent
--   4. Update indexes for efficient multi-checkpoint queries
--
-- This migration is IDEMPOTENT - safe to run multiple times.
-- Dependencies: 0001_init_memory_substrate.sql, 0012_fix_graph_checkpoints_unique.sql

-- =============================================================================
-- Step 1: Drop UNIQUE constraint on agent_id (if exists)
-- =============================================================================
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'graph_checkpoints_agent_id_key'
        AND conrelid = 'graph_checkpoints'::regclass
    ) THEN
        ALTER TABLE graph_checkpoints
        DROP CONSTRAINT graph_checkpoints_agent_id_key;
        RAISE NOTICE 'Dropped UNIQUE constraint on graph_checkpoints.agent_id';
    ELSE
        RAISE NOTICE 'UNIQUE constraint on graph_checkpoints.agent_id does not exist (already dropped)';
    END IF;
END $$;

-- =============================================================================
-- Step 2: Add 'reason' column for checkpoint triggers
-- =============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'graph_checkpoints' AND column_name = 'reason'
    ) THEN
        ALTER TABLE graph_checkpoints
        ADD COLUMN reason TEXT NOT NULL DEFAULT 'manual';
        RAISE NOTICE 'Added reason column to graph_checkpoints';
    ELSE
        RAISE NOTICE 'reason column already exists in graph_checkpoints';
    END IF;
END $$;

-- =============================================================================
-- Step 3: Add 'checkpoint_number' column for ordering
-- =============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'graph_checkpoints' AND column_name = 'checkpoint_number'
    ) THEN
        ALTER TABLE graph_checkpoints
        ADD COLUMN checkpoint_number SERIAL;
        RAISE NOTICE 'Added checkpoint_number column to graph_checkpoints';
    ELSE
        RAISE NOTICE 'checkpoint_number column already exists in graph_checkpoints';
    END IF;
END $$;

-- =============================================================================
-- Step 4: Update indexes for multi-checkpoint queries
-- =============================================================================

-- Drop old single-agent index (no longer optimal)
DROP INDEX IF EXISTS idx_graph_checkpoints_agent_id;

-- Create composite index for agent + time queries (most common)
CREATE INDEX IF NOT EXISTS idx_graph_checkpoints_agent_updated
ON graph_checkpoints (agent_id, updated_at DESC);

-- Create index for reason-based queries (retention cleanup)
CREATE INDEX IF NOT EXISTS idx_graph_checkpoints_reason
ON graph_checkpoints (reason, updated_at DESC);

-- Create index for checkpoint number ordering
CREATE INDEX IF NOT EXISTS idx_graph_checkpoints_agent_number
ON graph_checkpoints (agent_id, checkpoint_number DESC);

-- =============================================================================
-- Step 5: Update table comment
-- =============================================================================
COMMENT ON TABLE graph_checkpoints IS 'Multi-checkpoint storage for agent state recovery. Supports retention policies (keep_last_n, daily/weekly/monthly). Per memory_spec_v3.0.yaml persistence layer.';
COMMENT ON COLUMN graph_checkpoints.reason IS 'Checkpoint trigger: on_agent_shutdown, on_session_boundary, on_critical_decision, scheduled_hourly, on_approval, manual';
COMMENT ON COLUMN graph_checkpoints.checkpoint_number IS 'Auto-incrementing number for ordering within agent checkpoints';

-- =============================================================================
-- Verification query (for manual check)
-- =============================================================================
-- Run after migration:
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'graph_checkpoints'
-- ORDER BY ordinal_position;
