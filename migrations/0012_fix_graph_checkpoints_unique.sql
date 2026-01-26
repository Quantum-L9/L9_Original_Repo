-- Migration: 0012_fix_graph_checkpoints_unique
-- Purpose: Add missing UNIQUE constraint on graph_checkpoints.agent_id
--
-- Background: The original migration 0001_init_memory_substrate.sql defined:
--   agent_id TEXT NOT NULL UNIQUE
-- But some VPS databases were created before this constraint was added.
-- The checkpoint_node in substrate_graph.py requires this for ON CONFLICT upsert.
--
-- This migration is IDEMPOTENT - safe to run multiple times.

-- Add unique constraint if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'graph_checkpoints_agent_id_key'
        AND conrelid = 'graph_checkpoints'::regclass
    ) THEN
        ALTER TABLE graph_checkpoints
        ADD CONSTRAINT graph_checkpoints_agent_id_key UNIQUE (agent_id);
        RAISE NOTICE 'Added UNIQUE constraint on graph_checkpoints.agent_id';
    ELSE
        RAISE NOTICE 'UNIQUE constraint on graph_checkpoints.agent_id already exists';
    END IF;
END $$;
