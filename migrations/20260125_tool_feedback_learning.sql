-- ============================================================================
-- L9 Tool Feedback Learning - Schema Migration
-- GMP-TFL-001: Enable closed-loop tool selection learning
-- Created: 2026-01-25
-- ============================================================================

BEGIN;

-- ============================================================================
-- Table: tool_execution_feedback
-- Purpose: Store task→tool→outcome mappings for learning
-- ============================================================================
CREATE TABLE IF NOT EXISTS tool_execution_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Task identification
    task_query TEXT NOT NULL,
    task_embedding vector(1536) NOT NULL,
    task_type VARCHAR(100),
    session_id VARCHAR(255),

    -- Tool execution outcome
    tool_name VARCHAR(255) NOT NULL,
    success BOOLEAN NOT NULL,
    execution_time_ms DOUBLE PRECISION NOT NULL,
    error_type VARCHAR(255),

    -- Context
    agent_id VARCHAR(255) NOT NULL,
    confidence_score DOUBLE PRECISION,
    discovery_rank INTEGER,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    request_id VARCHAR(255),

    CONSTRAINT chk_tool_feedback_confidence
        CHECK (confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1))
);

-- Embedding similarity search (ivfflat for pgvector)
CREATE INDEX IF NOT EXISTS idx_tool_feedback_embedding
    ON tool_execution_feedback
    USING ivfflat (task_embedding vector_cosine_ops)
    WITH (lists = 100);

-- Tool success lookups
CREATE INDEX IF NOT EXISTS idx_tool_feedback_tool_success
    ON tool_execution_feedback (tool_name, success, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tool_feedback_task_type
    ON tool_execution_feedback (task_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tool_feedback_agent
    ON tool_execution_feedback (agent_id, tool_name, created_at DESC);

-- ============================================================================
-- Materialized View: tool_success_rates_24h
-- Purpose: Fast lookup of recent success rates
-- ============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS tool_success_rates_24h AS
SELECT
    tool_name,
    task_type,
    COUNT(*) AS total_executions,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) AS successful_executions,
    (SUM(CASE WHEN success THEN 1 ELSE 0 END)::DOUBLE PRECISION / NULLIF(COUNT(*), 0)) AS success_rate,
    AVG(execution_time_ms) AS avg_latency_ms,
    MAX(created_at) AS last_execution
FROM tool_execution_feedback
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY tool_name, task_type;

CREATE UNIQUE INDEX IF NOT EXISTS idx_tool_success_rates_24h_lookup
    ON tool_success_rates_24h (tool_name, task_type);

COMMENT ON MATERIALIZED VIEW tool_success_rates_24h IS
    'Auto-refreshed regularly to expose 24h tool success rates';

-- Manual refresh function
CREATE OR REPLACE FUNCTION refresh_tool_success_rates()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY tool_success_rates_24h;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Table: tool_learning_alerts
-- Purpose: Track degraded / underutilized tools detected by analysis
-- ============================================================================
CREATE TABLE IF NOT EXISTS tool_learning_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_name VARCHAR(255) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,          -- 'degraded', 'underutilized', 'high_latency', 'other'
    severity VARCHAR(20) NOT NULL,            -- 'info', 'warning', 'critical'

    success_rate DOUBLE PRECISION,
    avg_latency_ms DOUBLE PRECISION,
    usage_count INTEGER,

    message TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(255),

    CONSTRAINT chk_tool_learning_alert_type
        CHECK (alert_type IN ('degraded', 'underutilized', 'high_latency', 'other')),
    CONSTRAINT chk_tool_learning_alert_severity
        CHECK (severity IN ('info', 'warning', 'critical'))
);

CREATE INDEX IF NOT EXISTS idx_tool_learning_alerts_unacked
    ON tool_learning_alerts (tool_name, created_at DESC)
    WHERE NOT acknowledged;

COMMIT;
