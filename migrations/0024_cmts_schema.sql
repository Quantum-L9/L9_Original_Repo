-- ============================================================================
-- Migration: 0024_cmts_schema.sql
-- Description: Code Mutation Tracking System (CMTS) database schema
-- Created: 2026-01-20
-- Author: GMP-107
-- ============================================================================

-- CMTS: Provides immutable audit trail for all code mutations
-- All operations are logged with before/after states for RCA and compliance

BEGIN;

-- Enum for mutation status
CREATE TYPE mutation_status AS ENUM (
    'pending',
    'in_progress',
    'success',
    'failure',
    'rolled_back'
);

-- Main mutations table
CREATE TABLE IF NOT EXISTS cmts_mutations (
    id SERIAL PRIMARY KEY,
    tracking_id VARCHAR(50) UNIQUE NOT NULL,  -- CMTS-{uuid}
    subsystem VARCHAR(100) NOT NULL,
    agent_id VARCHAR(100) NOT NULL,
    trace_id VARCHAR(100),  -- Correlation with pattern orchestrator

    -- Git tracking
    branch_name VARCHAR(255),
    commit_sha VARCHAR(64),
    pr_url TEXT,
    pr_number INTEGER,

    -- Status
    status mutation_status NOT NULL DEFAULT 'pending',
    error_message TEXT,

    -- Timestamps
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    -- Metadata (JSON)
    metadata JSONB DEFAULT '{}',

    -- Indexes
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- File snapshots (before/after states)
CREATE TABLE IF NOT EXISTS cmts_file_snapshots (
    id SERIAL PRIMARY KEY,
    mutation_id INTEGER NOT NULL REFERENCES cmts_mutations(id) ON DELETE CASCADE,
    snapshot_type VARCHAR(10) NOT NULL CHECK (snapshot_type IN ('before', 'after')),
    file_path TEXT NOT NULL,
    content_hash VARCHAR(64),  -- SHA-256
    line_count INTEGER DEFAULT 0,
    file_exists BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- File changes (created/modified/deleted)
CREATE TABLE IF NOT EXISTS cmts_file_changes (
    id SERIAL PRIMARY KEY,
    mutation_id INTEGER NOT NULL REFERENCES cmts_mutations(id) ON DELETE CASCADE,
    change_type VARCHAR(10) NOT NULL CHECK (change_type IN ('created', 'modified', 'deleted')),
    file_path TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_cmts_mutations_tracking_id ON cmts_mutations(tracking_id);
CREATE INDEX IF NOT EXISTS idx_cmts_mutations_subsystem ON cmts_mutations(subsystem);
CREATE INDEX IF NOT EXISTS idx_cmts_mutations_status ON cmts_mutations(status);
CREATE INDEX IF NOT EXISTS idx_cmts_mutations_started_at ON cmts_mutations(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_cmts_mutations_trace_id ON cmts_mutations(trace_id);

CREATE INDEX IF NOT EXISTS idx_cmts_snapshots_mutation_id ON cmts_file_snapshots(mutation_id);
CREATE INDEX IF NOT EXISTS idx_cmts_changes_mutation_id ON cmts_file_changes(mutation_id);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_cmts_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER cmts_mutations_updated_at
    BEFORE UPDATE ON cmts_mutations
    FOR EACH ROW
    EXECUTE FUNCTION update_cmts_updated_at();

-- RLS Policies (if using multi-tenant)
-- ALTER TABLE cmts_mutations ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY cmts_tenant_isolation ON cmts_mutations
--     FOR ALL USING (tenant_id = current_setting('app.tenant_id')::uuid);

COMMIT;

-- ============================================================================
-- Rollback Script (for reverting this migration)
-- ============================================================================
-- BEGIN;
-- DROP TABLE IF EXISTS cmts_file_changes;
-- DROP TABLE IF EXISTS cmts_file_snapshots;
-- DROP TABLE IF EXISTS cmts_mutations;
-- DROP TYPE IF EXISTS mutation_status;
-- COMMIT;
