-- =============================================================================
-- L9 Memory Substrate - Migration 0003
-- Purpose: Tasks table for OS/agent task tracking and debugging
-- =============================================================================
-- Apply AFTER 0002_enhance_packet_store.sql
-- =============================================================================

CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    type TEXT NOT NULL DEFAULT 'generic',
    status TEXT NOT NULL DEFAULT 'pending',
    payload JSONB,
    result JSONB,
    error TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITHOUT TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(type);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at DESC);

COMMENT ON TABLE tasks IS 'Task queue for OS and agent operations';

-- =============================================================================
-- End Migration 0003
-- =============================================================================
