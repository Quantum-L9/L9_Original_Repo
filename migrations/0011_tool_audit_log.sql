-- Migration: Add tool audit log table
-- Harvested from: L9-Implementation-Suite-Ready-to-Deploy.md
-- Purpose: Track all tool executions with cost and performance metrics

BEGIN;

CREATE TABLE IF NOT EXISTS tool_audit_log (
    id BIGSERIAL PRIMARY KEY,
    tool_name VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    input_data JSONB,
    output_data JSONB,
    duration_ms FLOAT NOT NULL,
    tokens_used INT DEFAULT 0,
    cost_usd FLOAT DEFAULT 0.0,
    error TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    request_id UUID
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tool_audit_agent_timestamp
    ON tool_audit_log (agent_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_tool_audit_tool_timestamp
    ON tool_audit_log (tool_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_tool_audit_request_id
    ON tool_audit_log (request_id);

COMMIT;
