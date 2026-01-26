-- =============================================================================
-- L9 Memory Substrate - Feedback & Effectiveness Tracking (from Emma Patterns)
-- Migration: 0009_feedback_and_effectiveness.sql
-- Version: 1.0.0
-- Author: Cursor Agent (via GMP)
-- Date: 2026-01-01
-- =============================================================================
--
-- PURPOSE: Add Emma's feedback loop patterns to L9 core:
--   1. feedback_events table - Structured feedback from Igor/users
--   2. Effectiveness tracking on reflection_store
--   3. Reflection effectiveness functions
--   4. Feedback processing function
--
-- DEPENDENCIES: 0008_memory_substrate_10x.sql must be applied first
-- BREAKING CHANGES: None - all additions are backward compatible
-- =============================================================================

BEGIN;

-- =============================================================================
-- TABLE: feedback_events (From Emma Pattern)
-- Purpose: Track explicit feedback on agent outputs for learning
-- =============================================================================

CREATE TABLE IF NOT EXISTS feedback_events (
    feedback_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- What produced the output being evaluated
    packet_id UUID REFERENCES packet_store(packet_id) ON DELETE SET NULL,
    reflection_id UUID REFERENCES reflection_store(reflection_id) ON DELETE SET NULL,
    task_id TEXT,

    -- Who gave the feedback
    agent_id TEXT NOT NULL,

    -- Feedback details
    feedback_type TEXT NOT NULL CHECK (feedback_type IN ('positive', 'negative', 'correction', 'preference', 'question', 'clarification')),
    feedback_text TEXT,
    sentiment_score FLOAT CHECK (sentiment_score >= -1.0 AND sentiment_score <= 1.0),

    -- Processing status
    was_processed BOOLEAN DEFAULT false,
    processed_at TIMESTAMPTZ,
    processing_notes TEXT,

    -- What was derived from this feedback
    derived_reflection_id UUID REFERENCES reflection_store(reflection_id) ON DELETE SET NULL,
    derived_fact_id UUID,  -- References knowledge_facts if feedback creates a new fact

    -- Multi-tenant identity (4 core fields)
    tenant_id UUID,
    org_id UUID,
    user_id UUID,
    correlation_id UUID DEFAULT uuid_generate_v4(),

    -- Tracing
    session_id TEXT,
    trace_id TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE feedback_events IS 'Explicit feedback from Igor/users for agent learning';
COMMENT ON COLUMN feedback_events.feedback_type IS 'Type: positive, negative, correction, preference, question, clarification';
COMMENT ON COLUMN feedback_events.sentiment_score IS 'Sentiment: -1.0 (very negative) to 1.0 (very positive)';
COMMENT ON COLUMN feedback_events.derived_reflection_id IS 'Reflection created from this feedback (if any)';

-- Indexes for feedback_events
CREATE INDEX IF NOT EXISTS idx_feedback_packet ON feedback_events(packet_id);
CREATE INDEX IF NOT EXISTS idx_feedback_reflection ON feedback_events(reflection_id);
CREATE INDEX IF NOT EXISTS idx_feedback_task ON feedback_events(task_id);
CREATE INDEX IF NOT EXISTS idx_feedback_agent ON feedback_events(agent_id);
CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback_events(feedback_type);
CREATE INDEX IF NOT EXISTS idx_feedback_processed ON feedback_events(was_processed);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_unprocessed ON feedback_events(was_processed) WHERE was_processed = false;

-- Multi-tenant indexes
CREATE INDEX IF NOT EXISTS idx_feedback_tenant ON feedback_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_feedback_org ON feedback_events(org_id);
CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback_events(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_corr ON feedback_events(correlation_id);


-- =============================================================================
-- ALTER TABLE: reflection_store (Add Effectiveness Tracking)
-- Purpose: Track how well reflections perform when applied
-- =============================================================================

-- Effectiveness tracking columns
ALTER TABLE reflection_store ADD COLUMN IF NOT EXISTS success_count INT DEFAULT 0;
ALTER TABLE reflection_store ADD COLUMN IF NOT EXISTS failure_count INT DEFAULT 0;
ALTER TABLE reflection_store ADD COLUMN IF NOT EXISTS effectiveness_score FLOAT;
ALTER TABLE reflection_store ADD COLUMN IF NOT EXISTS last_applied_at TIMESTAMPTZ;
ALTER TABLE reflection_store ADD COLUMN IF NOT EXISTS times_applied INT DEFAULT 0;

-- Index for effectiveness-based retrieval
CREATE INDEX IF NOT EXISTS idx_reflection_effectiveness ON reflection_store(effectiveness_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_reflection_applied ON reflection_store(last_applied_at DESC NULLS LAST);

COMMENT ON COLUMN reflection_store.success_count IS 'Number of times reflection was applied successfully';
COMMENT ON COLUMN reflection_store.failure_count IS 'Number of times reflection was applied but failed';
COMMENT ON COLUMN reflection_store.effectiveness_score IS 'Calculated: success_count / (success_count + failure_count)';
COMMENT ON COLUMN reflection_store.times_applied IS 'Total times this reflection was used';


-- =============================================================================
-- FUNCTIONS: Feedback & Effectiveness
-- =============================================================================

-- Function: Update reflection effectiveness
CREATE OR REPLACE FUNCTION update_reflection_effectiveness(
    r_id UUID,
    was_successful BOOLEAN
)
RETURNS FLOAT AS $$
DECLARE
    new_score FLOAT;
BEGIN
    IF was_successful THEN
        UPDATE reflection_store
        SET success_count = success_count + 1,
            times_applied = times_applied + 1,
            last_applied_at = NOW(),
            access_count = access_count + 1,
            last_accessed = NOW()
        WHERE reflection_id = r_id;
    ELSE
        UPDATE reflection_store
        SET failure_count = failure_count + 1,
            times_applied = times_applied + 1,
            last_applied_at = NOW(),
            access_count = access_count + 1,
            last_accessed = NOW()
        WHERE reflection_id = r_id;
    END IF;

    -- Recalculate effectiveness score
    UPDATE reflection_store
    SET effectiveness_score =
        CASE WHEN (success_count + failure_count) > 0
        THEN success_count::FLOAT / (success_count + failure_count)::FLOAT
        ELSE NULL END
    WHERE reflection_id = r_id
    RETURNING effectiveness_score INTO new_score;

    RETURN new_score;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_reflection_effectiveness IS 'Update reflection success/failure counts and recalculate effectiveness';


-- Function: Process feedback event
CREATE OR REPLACE FUNCTION process_feedback_event(p_feedback_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_feedback feedback_events;
    v_reflection_id UUID;
    v_result JSONB;
BEGIN
    -- Get feedback details
    SELECT * INTO v_feedback
    FROM feedback_events
    WHERE feedback_id = p_feedback_id;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'error', 'Feedback not found');
    END IF;

    -- If feedback is on a reflection, update its effectiveness
    IF v_feedback.reflection_id IS NOT NULL THEN
        IF v_feedback.feedback_type = 'positive' THEN
            PERFORM update_reflection_effectiveness(v_feedback.reflection_id, true);
        ELSIF v_feedback.feedback_type = 'negative' THEN
            PERFORM update_reflection_effectiveness(v_feedback.reflection_id, false);
        END IF;
    END IF;

    -- Create a new reflection for negative/correction feedback
    IF v_feedback.feedback_type IN ('negative', 'correction') AND v_feedback.feedback_text IS NOT NULL THEN
        INSERT INTO reflection_store (
            task_id,
            reflection_type,
            content,
            context,
            priority,
            source_agent,
            source_packet,
            tenant_id,
            org_id,
            user_id,
            correlation_id
        ) VALUES (
            v_feedback.task_id,
            'lesson',
            v_feedback.feedback_text,
            'Derived from feedback event ' || v_feedback.feedback_id::text,
            'high',  -- Feedback-derived reflections are high priority
            v_feedback.agent_id,
            v_feedback.packet_id,
            v_feedback.tenant_id,
            v_feedback.org_id,
            v_feedback.user_id,
            v_feedback.correlation_id
        ) RETURNING reflection_id INTO v_reflection_id;

        -- Link back to feedback
        UPDATE feedback_events
        SET derived_reflection_id = v_reflection_id
        WHERE feedback_id = p_feedback_id;
    END IF;

    -- Mark as processed
    UPDATE feedback_events
    SET
        was_processed = true,
        processed_at = NOW(),
        processing_notes = 'Auto-processed by system'
    WHERE feedback_id = p_feedback_id;

    -- Build result
    v_result := jsonb_build_object(
        'success', true,
        'feedback_type', v_feedback.feedback_type,
        'reflection_updated', v_feedback.reflection_id IS NOT NULL,
        'new_reflection_created', v_reflection_id IS NOT NULL,
        'new_reflection_id', v_reflection_id
    );

    RETURN v_result;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION process_feedback_event IS 'Process feedback: update effectiveness, optionally create reflection';


-- Function: Decay reflection confidence (for contradicting feedback)
CREATE OR REPLACE FUNCTION decay_reflection_confidence(
    r_id UUID,
    decay_factor FLOAT DEFAULT 0.1
)
RETURNS FLOAT AS $$
DECLARE
    new_confidence FLOAT;
BEGIN
    UPDATE reflection_store
    SET
        confidence = GREATEST(0.1, confidence - decay_factor)
    WHERE reflection_id = r_id
    RETURNING confidence INTO new_confidence;

    RETURN new_confidence;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION decay_reflection_confidence IS 'Decay reflection confidence when contradicted';


-- Function: Get high-effectiveness reflections for a task context
CREATE OR REPLACE FUNCTION get_effective_reflections(
    p_task_context TEXT,
    p_min_effectiveness FLOAT DEFAULT 0.6,
    p_limit INT DEFAULT 10
)
RETURNS TABLE (
    reflection_id UUID,
    content TEXT,
    reflection_type TEXT,
    effectiveness_score FLOAT,
    times_applied INT,
    confidence FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        r.reflection_id,
        r.content,
        r.reflection_type,
        r.effectiveness_score,
        r.times_applied,
        r.confidence
    FROM reflection_store r
    WHERE r.effectiveness_score IS NOT NULL
      AND r.effectiveness_score >= p_min_effectiveness
      AND r.times_applied >= 3  -- Minimum applications for reliability
      AND (r.expires_at IS NULL OR r.expires_at > NOW())
    ORDER BY
        r.effectiveness_score DESC,
        r.times_applied DESC,
        r.confidence DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_effective_reflections IS 'Get high-effectiveness reflections for agent context injection';


-- =============================================================================
-- MATERIALIZED VIEW: High-Effectiveness Reflections
-- Purpose: Fast lookup for proven reflections
-- =============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_effective_reflections AS
SELECT
    r.reflection_id,
    r.task_id,
    r.reflection_type,
    r.content,
    r.context,
    r.confidence,
    r.priority,
    r.effectiveness_score,
    r.success_count,
    r.failure_count,
    r.times_applied,
    r.last_applied_at,
    r.created_at,
    r.source_agent,
    r.entities,
    r.tags,
    -- Combined score: effectiveness * confidence * recency
    (COALESCE(r.effectiveness_score, 0.5) * 0.5) +
    (r.confidence * 0.3) +
    (POWER(0.5, EXTRACT(EPOCH FROM (NOW() - COALESCE(r.last_applied_at, r.created_at))) / (30 * 86400)) * 0.2)
    AS combined_score
FROM reflection_store r
WHERE r.effectiveness_score IS NOT NULL
  AND r.effectiveness_score >= 0.6
  AND r.times_applied >= 3
  AND (r.expires_at IS NULL OR r.expires_at > NOW())
ORDER BY combined_score DESC;

-- Unique index for CONCURRENTLY refresh
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_eff_refl_id ON mv_effective_reflections(reflection_id);
CREATE INDEX IF NOT EXISTS idx_mv_eff_refl_type ON mv_effective_reflections(reflection_type);
CREATE INDEX IF NOT EXISTS idx_mv_eff_refl_score ON mv_effective_reflections(combined_score DESC);
CREATE INDEX IF NOT EXISTS idx_mv_eff_refl_agent ON mv_effective_reflections(source_agent);

COMMENT ON MATERIALIZED VIEW mv_effective_reflections IS 'Fast lookup for proven high-effectiveness reflections';


-- =============================================================================
-- RLS: Row Level Security for feedback_events
-- =============================================================================

ALTER TABLE feedback_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback_events FORCE ROW LEVEL SECURITY;

-- Tenant isolation policy
DROP POLICY IF EXISTS feedback_events_tenant_isolation ON feedback_events;
CREATE POLICY feedback_events_tenant_isolation ON feedback_events
    FOR ALL
    USING (
        tenant_id IS NULL
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
    )
    WITH CHECK (
        tenant_id IS NULL
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
    );

-- Org isolation policy
DROP POLICY IF EXISTS feedback_events_org_isolation ON feedback_events;
CREATE POLICY feedback_events_org_isolation ON feedback_events
    FOR ALL
    USING (
        org_id IS NULL
        OR org_id = NULLIF(current_setting('app.org_id', true), '')::uuid
    )
    WITH CHECK (
        org_id IS NULL
        OR org_id = NULLIF(current_setting('app.org_id', true), '')::uuid
    );

-- Admin override policy
DROP POLICY IF EXISTS feedback_events_admin_override ON feedback_events;
CREATE POLICY feedback_events_admin_override ON feedback_events
    FOR ALL
    USING (
        COALESCE(current_setting('app.role', true), 'end_user') IN ('platform_admin', 'tenant_admin')
    )
    WITH CHECK (
        COALESCE(current_setting('app.role', true), 'end_user') IN ('platform_admin', 'tenant_admin')
    );


-- =============================================================================
-- SCHEDULED JOB: Refresh materialized view
-- =============================================================================

-- Add to refresh_memory_views procedure (from 0008)
CREATE OR REPLACE PROCEDURE refresh_memory_views()
LANGUAGE plpgsql AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_agent_recent_important;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_entity_graph;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_high_confidence_facts;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_reflection_patterns;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_effective_reflections;

    RAISE NOTICE 'Refreshed all memory materialized views including mv_effective_reflections';
END;
$$;


-- =============================================================================
-- MIGRATION COMPLETE
-- =============================================================================

DO $$
DECLARE
    feedback_exists BOOLEAN;
    effectiveness_col_exists BOOLEAN;
BEGIN
    -- Check feedback_events table
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'feedback_events'
    ) INTO feedback_exists;

    -- Check effectiveness columns on reflection_store
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'reflection_store'
          AND column_name = 'effectiveness_score'
    ) INTO effectiveness_col_exists;

    IF feedback_exists AND effectiveness_col_exists THEN
        RAISE NOTICE '✅ Migration 0009_feedback_and_effectiveness.sql completed successfully';
        RAISE NOTICE '   - feedback_events table created';
        RAISE NOTICE '   - reflection_store enhanced with effectiveness tracking';
        RAISE NOTICE '   - 4 functions created: update_reflection_effectiveness, process_feedback_event, decay_reflection_confidence, get_effective_reflections';
        RAISE NOTICE '   - mv_effective_reflections materialized view created';
        RAISE NOTICE '   - RLS policies applied to feedback_events';
        RAISE NOTICE '   - refresh_memory_views procedure updated';
    ELSE
        RAISE WARNING '⚠️ Migration may be incomplete. feedback_events: %, effectiveness_score: %', feedback_exists, effectiveness_col_exists;
    END IF;
END
$$;

COMMIT;

-- =============================================================================
-- POST-MIGRATION: How to Use
-- =============================================================================
--
-- 1. Record feedback on an agent output:
--    INSERT INTO feedback_events (packet_id, agent_id, feedback_type, feedback_text)
--    VALUES ('packet-uuid', 'L', 'negative', 'This response was too verbose');
--
-- 2. Process the feedback (updates effectiveness, may create reflection):
--    SELECT process_feedback_event('feedback-uuid');
--
-- 3. Track reflection effectiveness when applying:
--    -- After applying a reflection successfully:
--    SELECT update_reflection_effectiveness('reflection-uuid', true);
--    -- After applying a reflection that failed:
--    SELECT update_reflection_effectiveness('reflection-uuid', false);
--
-- 4. Get high-effectiveness reflections for context:
--    SELECT * FROM get_effective_reflections('code review', 0.7, 5);
--
-- 5. Query the materialized view for fast lookups:
--    SELECT * FROM mv_effective_reflections
--    WHERE reflection_type = 'lesson'
--    ORDER BY combined_score DESC
--    LIMIT 10;
--
-- =============================================================================
-- END MIGRATION 0009
-- =============================================================================
