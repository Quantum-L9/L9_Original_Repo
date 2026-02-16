-- Migration: 0032_fix_timestamp_timezones.sql
-- Description: Alter naive timestamp columns to timestamp with time zone to ensure ADR-0083 compliance and resolve ingestion errors.
-- Handling dependencies: Drops and recreates dependent materialized views.
-- Created: 2026-02-13 06:30 EST

-- 0. Drop dependent materialized views
DROP MATERIALIZED VIEW IF EXISTS mv_agent_recent_important;
DROP MATERIALIZED VIEW IF EXISTS mv_high_confidence_facts;
DROP MATERIALIZED VIEW IF EXISTS mv_reflection_patterns;
DROP MATERIALIZED VIEW IF EXISTS mv_effective_reflections;
DROP MATERIALIZED VIEW IF EXISTS tool_success_rates_24h;
DROP MATERIALIZED VIEW IF EXISTS mv_entity_graph;

-- 1. packet_store
ALTER TABLE packet_store ALTER COLUMN ttl TYPE timestamp with time zone USING ttl AT TIME ZONE 'UTC';
ALTER TABLE packet_store ALTER COLUMN timestamp TYPE timestamp with time zone USING timestamp AT TIME ZONE 'UTC';

-- 2. knowledge_facts
ALTER TABLE knowledge_facts ALTER COLUMN created_at TYPE timestamp with time zone USING created_at AT TIME ZONE 'UTC';
ALTER TABLE knowledge_facts ALTER COLUMN deprecated_at TYPE timestamp with time zone USING deprecated_at AT TIME ZONE 'UTC';

-- 3. semantic_memory
ALTER TABLE semantic_memory ALTER COLUMN created_at TYPE timestamp with time zone USING created_at AT TIME ZONE 'UTC';

-- 4. graph_checkpoints
ALTER TABLE graph_checkpoints ALTER COLUMN updated_at TYPE timestamp with time zone USING updated_at AT TIME ZONE 'UTC';

-- 5. reasoning_traces
ALTER TABLE reasoning_traces ALTER COLUMN created_at TYPE timestamp with time zone USING created_at AT TIME ZONE 'UTC';

-- 6. agent_memory_events
ALTER TABLE agent_memory_events ALTER COLUMN timestamp TYPE timestamp with time zone USING timestamp AT TIME ZONE 'UTC';

-- 7. episodic_events
ALTER TABLE episodic_events ALTER COLUMN event_timestamp TYPE timestamp with time zone USING event_timestamp AT TIME ZONE 'UTC';
ALTER TABLE episodic_events ALTER COLUMN created_at TYPE timestamp with time zone USING created_at AT TIME ZONE 'UTC';
ALTER TABLE episodic_events ALTER COLUMN updated_at TYPE timestamp with time zone USING updated_at AT TIME ZONE 'UTC';

-- 8. semantic_facts
ALTER TABLE semantic_facts ALTER COLUMN valid_from TYPE timestamp with time zone USING valid_from AT TIME ZONE 'UTC';
ALTER TABLE semantic_facts ALTER COLUMN valid_to TYPE timestamp with time zone USING valid_to AT TIME ZONE 'UTC';

-- 9. agent_log
ALTER TABLE agent_log ALTER COLUMN timestamp TYPE timestamp with time zone USING timestamp AT TIME ZONE 'UTC';

-- 10. Recreate materialized views

-- mv_agent_recent_important (from 0008)
CREATE MATERIALIZED VIEW mv_agent_recent_important AS
SELECT
    e.agent_id,
    p.packet_id,
    p.packet_type,
    p.timestamp,
    p.importance_score,
    p.access_count,
    p.tags,
    p.scope,
    combined_importance(
        p.importance_score,
        p.access_count,
        p.last_accessed,
        p.timestamp
    ) as combined_score
FROM packet_store p
JOIN agent_memory_events e ON p.packet_id = e.packet_id
WHERE p.timestamp > NOW() - INTERVAL '30 days'
  AND p.importance_score > 0.3
ORDER BY e.agent_id, combined_importance(p.importance_score, p.access_count, p.last_accessed, p.timestamp) DESC;

CREATE UNIQUE INDEX idx_mv_agent_recent ON mv_agent_recent_important(agent_id, packet_id);
CREATE INDEX idx_mv_agent_score ON mv_agent_recent_important(agent_id, combined_score DESC);

-- mv_high_confidence_facts (from 0008)
CREATE MATERIALIZED VIEW mv_high_confidence_facts AS
SELECT
    f.fact_id,
    f.subject,
    f.subject_normalized,
    f.predicate,
    f.object,
    f.confidence,
    f.supporting_packet_count,
    f.access_count,
    combined_importance(
        f.confidence,
        f.access_count,
        f.last_accessed,
        f.created_at
    ) as combined_score
FROM knowledge_facts f
WHERE f.confidence >= 0.6
  AND f.contradiction_count < 3
ORDER BY combined_importance(f.confidence, f.access_count, f.last_accessed, f.created_at) DESC;

CREATE UNIQUE INDEX idx_mv_facts_id ON mv_high_confidence_facts(fact_id);
CREATE INDEX idx_mv_facts_subject ON mv_high_confidence_facts(subject_normalized);
CREATE INDEX idx_mv_facts_score ON mv_high_confidence_facts(combined_score DESC);

-- mv_reflection_patterns (from 0008)
CREATE MATERIALIZED VIEW mv_reflection_patterns AS
SELECT
    reflection_type,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence,
    ARRAY_AGG(DISTINCT unnested_tag) as all_tags,
    MAX(created_at) as latest
FROM reflection_store,
     LATERAL unnest(tags) as unnested_tag
GROUP BY reflection_type;

CREATE UNIQUE INDEX idx_mv_refl_type ON mv_reflection_patterns(reflection_type);

-- mv_effective_reflections (from 0009)
CREATE MATERIALIZED VIEW mv_effective_reflections AS
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

CREATE UNIQUE INDEX idx_mv_eff_refl_id ON mv_effective_reflections(reflection_id);
CREATE INDEX idx_mv_eff_refl_type ON mv_effective_reflections(reflection_type);
CREATE INDEX idx_mv_eff_refl_score ON mv_effective_reflections(combined_score DESC);
CREATE INDEX idx_mv_eff_refl_agent ON mv_effective_reflections(source_agent);

-- tool_success_rates_24h (from 20260125_tool_feedback_learning.sql)
CREATE MATERIALIZED VIEW tool_success_rates_24h AS
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

CREATE UNIQUE INDEX idx_tool_success_rates_24h_lookup ON tool_success_rates_24h (tool_name, task_type);

-- mv_entity_graph (from 0008)
CREATE MATERIALIZED VIEW mv_entity_graph AS
SELECT
    source_entity,
    relationship_type,
    target_entity,
    SUM(mention_count) as total_mentions,
    MAX(confidence) as max_confidence,
    AVG(confidence) as avg_confidence,
    MAX(last_seen) as last_seen,
    COUNT(*) as relationship_count
FROM entity_relationships
GROUP BY source_entity, relationship_type, target_entity
HAVING SUM(mention_count) >= 1;

CREATE UNIQUE INDEX idx_mv_entity_unique ON mv_entity_graph(source_entity, relationship_type, target_entity);
CREATE INDEX idx_mv_entity_source ON mv_entity_graph(source_entity);
CREATE INDEX idx_mv_entity_target ON mv_entity_graph(target_entity);
CREATE INDEX idx_mv_entity_mentions ON mv_entity_graph(total_mentions DESC);
