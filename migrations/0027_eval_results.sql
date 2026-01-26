-- Migration: 0027_eval_results.sql
-- Purpose: Evaluation results storage for baseline tracking and regression detection
-- Created: 2026-01-25
-- GMP: Agent Initialization - Paradigm Shift (Evaluation Framework)

-- =============================================================================
-- EVAL RESULTS TABLE
-- Stores evaluation run results for baseline comparison and CI/CD gating
-- =============================================================================

CREATE TABLE IF NOT EXISTS eval_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Evaluation metadata
    eval_set_name VARCHAR(255) NOT NULL,
    agent_id VARCHAR(50) NOT NULL,
    version VARCHAR(100) NOT NULL DEFAULT 'latest',
    
    -- Core metrics
    success_rate FLOAT NOT NULL,
    avg_latency_ms FLOAT,
    tool_accuracy FLOAT,
    llm_judge_score FLOAT,
    
    -- Additional metrics (optional)
    examples_run INTEGER,
    examples_passed INTEGER,
    error_count INTEGER DEFAULT 0,
    p95_latency_ms FLOAT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Optional: Link to CI/CD run
    ci_run_id VARCHAR(255),
    commit_sha VARCHAR(64),
    branch VARCHAR(255)
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Primary lookup: agent + eval set + time (for baseline retrieval)
CREATE INDEX IF NOT EXISTS idx_eval_results_agent_set_time 
    ON eval_results(agent_id, eval_set_name, created_at DESC);

-- Version lookup (for specific version comparison)
CREATE INDEX IF NOT EXISTS idx_eval_results_version 
    ON eval_results(agent_id, eval_set_name, version);

-- CI/CD lookup (for build status queries)
CREATE INDEX IF NOT EXISTS idx_eval_results_ci_run 
    ON eval_results(ci_run_id) WHERE ci_run_id IS NOT NULL;

-- Time-based cleanup queries
CREATE INDEX IF NOT EXISTS idx_eval_results_created_at 
    ON eval_results(created_at);

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE eval_results IS 'Stores evaluation run results for baseline tracking and regression detection';
COMMENT ON COLUMN eval_results.eval_set_name IS 'Name of the evaluation set (e.g., information_retrieval, code_analysis)';
COMMENT ON COLUMN eval_results.success_rate IS 'Task success rate (0.0 to 1.0)';
COMMENT ON COLUMN eval_results.llm_judge_score IS 'LLM-as-judge quality score (0.0 to 1.0)';
COMMENT ON COLUMN eval_results.tool_accuracy IS 'Tool selection accuracy (Jaccard similarity)';

-- =============================================================================
-- RETENTION POLICY VIEW (Optional: For cleanup jobs)
-- =============================================================================

CREATE OR REPLACE VIEW eval_results_retention AS
SELECT 
    id,
    eval_set_name,
    agent_id,
    created_at,
    CASE 
        WHEN created_at < NOW() - INTERVAL '90 days' THEN 'archive'
        WHEN created_at < NOW() - INTERVAL '30 days' THEN 'compress'
        ELSE 'keep'
    END as retention_action
FROM eval_results;

-- =============================================================================
-- BASELINE LOOKUP FUNCTION
-- =============================================================================

CREATE OR REPLACE FUNCTION get_latest_baseline(
    p_agent_id VARCHAR(50),
    p_eval_set_name VARCHAR(255)
)
RETURNS TABLE (
    id UUID,
    version VARCHAR(100),
    success_rate FLOAT,
    avg_latency_ms FLOAT,
    tool_accuracy FLOAT,
    llm_judge_score FLOAT,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        er.id,
        er.version,
        er.success_rate,
        er.avg_latency_ms,
        er.tool_accuracy,
        er.llm_judge_score,
        er.created_at
    FROM eval_results er
    WHERE er.agent_id = p_agent_id 
      AND er.eval_set_name = p_eval_set_name
    ORDER BY er.created_at DESC
    LIMIT 1;
END;
$$;

COMMENT ON FUNCTION get_latest_baseline IS 'Retrieves the most recent baseline for an agent/eval_set combination';
