-- Migration: 0021_gmp_learning.sql
-- Description: GMP v2.0 Meta-Learning System tables
-- Author: GMP-90
-- Date: 2026-01-15
--
-- Tables:
--   - gmp_execution_history: Tracks GMP execution results for pattern analysis
--   - learned_heuristics: Stores learned patterns with confidence scores
--   - autonomy_graduation_metrics: Tracks L2→L3→L4→L5 progression
--
-- Dependencies: None (standalone tables)

-- ============================================================================
-- TABLE: gmp_execution_history
-- Purpose: Log every GMP execution for pattern analysis and learning
-- ============================================================================
CREATE TABLE IF NOT EXISTS gmp_execution_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gmp_id VARCHAR(255) NOT NULL UNIQUE,
    task_type VARCHAR(100) NOT NULL,
    todo_count INTEGER NOT NULL CHECK (todo_count >= 0),
    execution_minutes FLOAT NOT NULL CHECK (execution_minutes >= 0),
    error_count INTEGER NOT NULL DEFAULT 0 CHECK (error_count >= 0),
    error_types TEXT[] NOT NULL DEFAULT '{}',
    files_modified TEXT[] NOT NULL DEFAULT '{}',
    lines_changed INTEGER NOT NULL DEFAULT 0 CHECK (lines_changed >= 0),
    final_confidence FLOAT NOT NULL CHECK (final_confidence >= 0 AND final_confidence <= 100),
    audit_result VARCHAR(20) NOT NULL CHECK (audit_result IN ('PASS', 'CONDITIONAL', 'FAIL')),
    l9_kernel_versions JSONB NOT NULL DEFAULT '{}',
    feature_flags_enabled TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for gmp_execution_history
CREATE INDEX IF NOT EXISTS idx_gmp_execution_gmp_id 
    ON gmp_execution_history(gmp_id);

CREATE INDEX IF NOT EXISTS idx_gmp_execution_task_type 
    ON gmp_execution_history(task_type);

CREATE INDEX IF NOT EXISTS idx_gmp_execution_created_at 
    ON gmp_execution_history(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_gmp_execution_task_type_confidence 
    ON gmp_execution_history(task_type, final_confidence);

CREATE INDEX IF NOT EXISTS idx_gmp_execution_error_analysis 
    ON gmp_execution_history(error_count, created_at DESC);

-- ============================================================================
-- TABLE: learned_heuristics
-- Purpose: Store patterns learned from execution history
-- ============================================================================
CREATE TABLE IF NOT EXISTS learned_heuristics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    heuristic_id VARCHAR(255) NOT NULL UNIQUE,
    pattern_text TEXT NOT NULL,
    condition TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    supporting_gmp_ids TEXT[] NOT NULL DEFAULT '{}',
    impact_estimate VARCHAR(50) NOT NULL,
    generated_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Indexes for learned_heuristics
CREATE INDEX IF NOT EXISTS idx_heuristics_heuristic_id 
    ON learned_heuristics(heuristic_id);

CREATE INDEX IF NOT EXISTS idx_heuristics_confidence 
    ON learned_heuristics(confidence DESC) 
    WHERE active = TRUE;

CREATE INDEX IF NOT EXISTS idx_heuristics_generated_date 
    ON learned_heuristics(generated_date DESC);

CREATE INDEX IF NOT EXISTS idx_heuristics_active 
    ON learned_heuristics(active) 
    WHERE active = TRUE;

-- ============================================================================
-- TABLE: autonomy_graduation_metrics
-- Purpose: Track L2→L3→L4→L5 autonomy progression
-- ============================================================================
CREATE TABLE IF NOT EXISTS autonomy_graduation_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    current_level VARCHAR(10) NOT NULL DEFAULT 'L2' CHECK (current_level IN ('L2', 'L3', 'L4', 'L5')),
    perfect_executions_l2 INTEGER NOT NULL DEFAULT 0 CHECK (perfect_executions_l2 >= 0),
    consistency_score_l3 FLOAT NOT NULL DEFAULT 0.0 CHECK (consistency_score_l3 >= 0 AND consistency_score_l3 <= 1),
    safety_audit_passed_l4 BOOLEAN NOT NULL DEFAULT FALSE,
    l2_to_l3_ready BOOLEAN NOT NULL DEFAULT FALSE,
    l3_to_l4_ready BOOLEAN NOT NULL DEFAULT FALSE,
    l4_to_l5_ready BOOLEAN NOT NULL DEFAULT FALSE,
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Trigger to auto-update last_updated
CREATE OR REPLACE FUNCTION update_autonomy_metrics_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_autonomy_metrics_timestamp ON autonomy_graduation_metrics;
CREATE TRIGGER trg_autonomy_metrics_timestamp
    BEFORE UPDATE ON autonomy_graduation_metrics
    FOR EACH ROW
    EXECUTE FUNCTION update_autonomy_metrics_timestamp();

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE gmp_execution_history IS 'GMP v2.0: Execution history for meta-learning pattern analysis';
COMMENT ON TABLE learned_heuristics IS 'GMP v2.0: Learned patterns with confidence scores for future GMPs';
COMMENT ON TABLE autonomy_graduation_metrics IS 'GMP v2.0: Tracks L2→L3→L4→L5 autonomy level progression';

COMMENT ON COLUMN gmp_execution_history.gmp_id IS 'Unique GMP identifier (e.g., GMP-89-Integration)';
COMMENT ON COLUMN gmp_execution_history.task_type IS 'Type of task (refactor, schema, feature, etc.)';
COMMENT ON COLUMN gmp_execution_history.final_confidence IS 'Audit confidence score 0-100';
COMMENT ON COLUMN gmp_execution_history.audit_result IS 'PASS, CONDITIONAL, or FAIL';

COMMENT ON COLUMN learned_heuristics.confidence IS 'Confidence score 0-1 for this heuristic';
COMMENT ON COLUMN learned_heuristics.impact_estimate IS 'Expected impact: faster, fewer_errors, safer, etc.';

COMMENT ON COLUMN autonomy_graduation_metrics.current_level IS 'Current autonomy level: L2, L3, L4, or L5';
COMMENT ON COLUMN autonomy_graduation_metrics.perfect_executions_l2 IS 'Consecutive perfect L2 executions (resets on error)';
COMMENT ON COLUMN autonomy_graduation_metrics.consistency_score_l3 IS 'Consistency metric 0-1 for L3→L4 graduation';

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    -- Verify tables exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'gmp_execution_history') THEN
        RAISE EXCEPTION 'Table gmp_execution_history was not created';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'learned_heuristics') THEN
        RAISE EXCEPTION 'Table learned_heuristics was not created';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'autonomy_graduation_metrics') THEN
        RAISE EXCEPTION 'Table autonomy_graduation_metrics was not created';
    END IF;
    
    RAISE NOTICE 'Migration 0021_gmp_learning.sql completed successfully';
END $$;
