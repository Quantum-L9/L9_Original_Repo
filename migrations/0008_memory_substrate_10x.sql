-- =============================================================================
-- L9 Memory Substrate - 10X Upgrade Migration (Multi-Tenant Edition)
-- Migration: 0008_memory_substrate_10x.sql
-- Version: 2.1.0
-- Author: L9 System (via 7-Block Reasoning Analysis)
-- Date: 2026-01-01
-- =============================================================================
--
-- PURPOSE: 10X improvement to memory substrate for:
--   - Accuracy: Multi-vector embeddings, confidence decay
--   - Efficiency: Access-based importance, optimized indexes
--   - Ingestion: Chunking support, entity extraction
--   - Retrieval: Hybrid search, temporal weighting
--   - Self-Reflection: Persistent reflections, pattern learning
--   - Multi-Tenancy: Full tenant/org/user isolation with RLS
--
-- MULTI-TENANT IDENTITY FIELDS (4 core + tracing):
--   1. tenant_id (uuid) - Top-level tenant isolation
--   2. org_id (uuid) - Organization within tenant
--   3. user_id (uuid) - User within organization
--   4. correlation_id (uuid) - Request/session correlation
--   + session_id, trace_id, packet_id for tracing
--
-- SESSION VARIABLES (set before queries):
--   - app.tenant_id
--   - app.org_id
--   - app.user_id
--   - app.role ('platform_admin', 'tenant_admin', 'org_admin', 'end_user')
--
-- DEPENDENCIES: 0001-0007 migrations must be applied first
-- BREAKING CHANGES: None - all additions are backward compatible
-- =============================================================================

BEGIN;

-- Enable required extensions (may already exist)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- =============================================================================
-- MULTI-TENANT HELPER FUNCTIONS
-- =============================================================================

-- Function: Set session scope for RLS policies
CREATE OR REPLACE FUNCTION l9_set_scope(
    p_tenant uuid,
    p_org uuid,
    p_user uuid,
    p_role text DEFAULT 'end_user'
)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM set_config('app.tenant_id', p_tenant::text, true);
    PERFORM set_config('app.org_id', p_org::text, true);
    PERFORM set_config('app.user_id', p_user::text, true);
    PERFORM set_config('app.role', p_role::text, true);
END;
$$;

COMMENT ON FUNCTION l9_set_scope IS 'Set session scope variables for RLS policies';

-- Function: Get current tenant (for use in defaults)
CREATE OR REPLACE FUNCTION l9_current_tenant()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
    SELECT NULLIF(current_setting('app.tenant_id', true), '')::uuid;
$$;

-- Function: Get current org
CREATE OR REPLACE FUNCTION l9_current_org()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
    SELECT NULLIF(current_setting('app.org_id', true), '')::uuid;
$$;

-- Function: Get current user
CREATE OR REPLACE FUNCTION l9_current_user_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
    SELECT NULLIF(current_setting('app.user_id', true), '')::uuid;
$$;

-- Function: Get current role
CREATE OR REPLACE FUNCTION l9_current_role()
RETURNS text
LANGUAGE sql
STABLE
AS $$
    SELECT COALESCE(NULLIF(current_setting('app.role', true), ''), 'end_user');
$$;

-- Function: Check if current session is admin
CREATE OR REPLACE FUNCTION l9_is_admin()
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT l9_current_role() IN ('platform_admin', 'tenant_admin', 'org_admin');
$$;

-- Function: Compute SHA256 hash of JSONB (for content_hash)
CREATE OR REPLACE FUNCTION l9_sha256_jsonb(j jsonb)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT encode(digest(convert_to(j::text, 'UTF8'), 'sha256'), 'hex');
$$;

COMMENT ON FUNCTION l9_sha256_jsonb IS 'Compute SHA256 hash of JSONB for content deduplication';

-- =============================================================================
-- TABLE: memory_embeddings (Multi-Space Vector Storage)
-- Purpose: Store multiple embedding types per packet for precision retrieval
-- Types: 'content' (what), 'context' (when/where), 'entity' (who/what), 'summary'
-- =============================================================================
CREATE TABLE IF NOT EXISTS memory_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    packet_id UUID REFERENCES packet_store(packet_id) ON DELETE CASCADE,
    embedding_type TEXT NOT NULL CHECK (embedding_type IN ('content', 'context', 'entity', 'summary', 'reasoning')),
    vector VECTOR(1536) NOT NULL,
    chunk_index INT DEFAULT 0,              -- For chunked content (0 = full, 1+ = chunks)
    chunk_text TEXT,                        -- Stored chunk for debugging/display
    metadata JSONB DEFAULT '{}',            -- Additional embedding metadata
    -- Multi-tenant identity (4 core fields)
    tenant_id UUID,
    org_id UUID,
    user_id UUID,
    correlation_id UUID DEFAULT uuid_generate_v4(),
    -- Tracing
    session_id TEXT,
    trace_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE memory_embeddings IS 'Multi-space vector embeddings for precision semantic search';
COMMENT ON COLUMN memory_embeddings.embedding_type IS 'Type of embedding: content, context, entity, summary, reasoning';
COMMENT ON COLUMN memory_embeddings.chunk_index IS 'Index for chunked documents (0=full, 1+=chunks)';

-- Indexes for memory_embeddings
CREATE INDEX IF NOT EXISTS idx_embeddings_packet ON memory_embeddings(packet_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_type ON memory_embeddings(embedding_type);
CREATE INDEX IF NOT EXISTS idx_embeddings_created ON memory_embeddings(created_at DESC);

-- Type-specific HNSW indexes for efficient per-type vector search
CREATE INDEX IF NOT EXISTS idx_embeddings_vector_content ON memory_embeddings
    USING hnsw (vector vector_cosine_ops)
    WHERE embedding_type = 'content';

CREATE INDEX IF NOT EXISTS idx_embeddings_vector_entity ON memory_embeddings
    USING hnsw (vector vector_cosine_ops)
    WHERE embedding_type = 'entity';

CREATE INDEX IF NOT EXISTS idx_embeddings_vector_summary ON memory_embeddings
    USING hnsw (vector vector_cosine_ops)
    WHERE embedding_type = 'summary';

-- Multi-tenant indexes for memory_embeddings
CREATE INDEX IF NOT EXISTS idx_embeddings_tenant ON memory_embeddings(tenant_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_org ON memory_embeddings(org_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_user ON memory_embeddings(user_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_corr ON memory_embeddings(correlation_id);


-- =============================================================================
-- TABLE: memory_access_log (Usage Tracking)
-- Purpose: Track what memories are accessed to learn importance
-- =============================================================================
CREATE TABLE IF NOT EXISTS memory_access_log (
    access_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    target_type TEXT NOT NULL CHECK (target_type IN ('packet', 'embedding', 'fact', 'reflection', 'summary')),
    target_id UUID NOT NULL,
    agent_id TEXT NOT NULL,
    access_context TEXT,                    -- Why this access happened
    query_text TEXT,                        -- What search triggered this
    relevance_score FLOAT,                  -- Search score if from search
    was_useful BOOLEAN,                     -- Explicit feedback (null = unknown)
    feedback_reason TEXT,                   -- Why useful/not useful
    -- Multi-tenant identity (4 core fields)
    tenant_id UUID,
    org_id UUID,
    user_id UUID,
    correlation_id UUID DEFAULT uuid_generate_v4(),
    -- Tracing
    session_id TEXT,
    trace_id TEXT,
    accessed_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE memory_access_log IS 'Tracks memory access patterns for importance learning';
COMMENT ON COLUMN memory_access_log.was_useful IS 'Explicit feedback: true=helpful, false=not helpful, null=unknown';

CREATE INDEX IF NOT EXISTS idx_access_target ON memory_access_log(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_access_agent ON memory_access_log(agent_id);
CREATE INDEX IF NOT EXISTS idx_access_time ON memory_access_log(accessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_access_useful ON memory_access_log(was_useful) WHERE was_useful IS NOT NULL;

-- Multi-tenant indexes for memory_access_log
CREATE INDEX IF NOT EXISTS idx_access_tenant ON memory_access_log(tenant_id);
CREATE INDEX IF NOT EXISTS idx_access_org ON memory_access_log(org_id);
CREATE INDEX IF NOT EXISTS idx_access_user ON memory_access_log(user_id);
CREATE INDEX IF NOT EXISTS idx_access_corr ON memory_access_log(correlation_id);


-- =============================================================================
-- TABLE: entity_relationships (Knowledge Graph Edges)
-- Purpose: Explicit entity-to-entity relationships for graph traversal
-- =============================================================================
CREATE TABLE IF NOT EXISTS entity_relationships (
    relationship_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_entity TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    target_entity TEXT NOT NULL,
    confidence FLOAT DEFAULT 0.8 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    source_packet UUID REFERENCES packet_store(packet_id) ON DELETE SET NULL,
    mention_count INT DEFAULT 1,
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    -- Multi-tenant identity (4 core fields)
    tenant_id UUID,
    org_id UUID,
    user_id UUID,
    correlation_id UUID DEFAULT uuid_generate_v4()
);

COMMENT ON TABLE entity_relationships IS 'Entity relationship graph for knowledge traversal';
COMMENT ON COLUMN entity_relationships.mention_count IS 'Number of times this relationship observed';

CREATE INDEX IF NOT EXISTS idx_rel_source ON entity_relationships(source_entity);
CREATE INDEX IF NOT EXISTS idx_rel_target ON entity_relationships(target_entity);
CREATE INDEX IF NOT EXISTS idx_rel_type ON entity_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_rel_confidence ON entity_relationships(confidence DESC);

-- Multi-tenant indexes for entity_relationships
CREATE INDEX IF NOT EXISTS idx_rel_tenant ON entity_relationships(tenant_id);
CREATE INDEX IF NOT EXISTS idx_rel_org ON entity_relationships(org_id);
CREATE INDEX IF NOT EXISTS idx_rel_user ON entity_relationships(user_id);
CREATE INDEX IF NOT EXISTS idx_rel_corr ON entity_relationships(correlation_id);

-- Unique constraint to enable UPSERT for relationship reinforcement (scoped by tenant)
CREATE UNIQUE INDEX IF NOT EXISTS idx_rel_unique
    ON entity_relationships(tenant_id, source_entity, relationship_type, target_entity);


-- =============================================================================
-- TABLE: memory_summaries (Consolidated Memories)
-- Purpose: Compressed summaries of old content for efficient long-term memory
-- =============================================================================
CREATE TABLE IF NOT EXISTS memory_summaries (
    summary_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scope_type TEXT NOT NULL CHECK (scope_type IN ('thread', 'agent', 'topic', 'time_period', 'project', 'task')),
    scope_value TEXT NOT NULL,              -- e.g., thread_id, agent_id, topic name, '2026-01'
    summary_text TEXT NOT NULL,
    key_facts JSONB DEFAULT '[]',           -- Extracted important facts as array
    key_entities TEXT[] DEFAULT '{}',       -- Entity names mentioned
    key_decisions TEXT[] DEFAULT '{}',      -- Decision points
    source_packet_ids UUID[] DEFAULT '{}',  -- Packets that were summarized
    packet_count INT DEFAULT 0,
    vector VECTOR(1536),                    -- Embedded summary for search
    confidence FLOAT DEFAULT 0.7 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    coverage_start TIMESTAMPTZ,             -- Time range covered
    coverage_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ,                -- When summary should be regenerated
    created_by TEXT DEFAULT 'system',
    -- Multi-tenant identity (4 core fields)
    tenant_id UUID,
    org_id UUID,
    user_id UUID,
    correlation_id UUID DEFAULT uuid_generate_v4()
);

COMMENT ON TABLE memory_summaries IS 'Consolidated summaries for long-term memory efficiency';
COMMENT ON COLUMN memory_summaries.scope_type IS 'What this summary covers: thread, agent, topic, time_period, project, task';
COMMENT ON COLUMN memory_summaries.valid_until IS 'Expiration trigger for regeneration';

CREATE INDEX IF NOT EXISTS idx_summary_scope ON memory_summaries(scope_type, scope_value);
CREATE INDEX IF NOT EXISTS idx_summary_created ON memory_summaries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_summary_valid ON memory_summaries(valid_until) WHERE valid_until IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_summary_entities ON memory_summaries USING GIN(key_entities);

-- Multi-tenant indexes for memory_summaries
CREATE INDEX IF NOT EXISTS idx_summary_tenant ON memory_summaries(tenant_id);
CREATE INDEX IF NOT EXISTS idx_summary_org ON memory_summaries(org_id);
CREATE INDEX IF NOT EXISTS idx_summary_user ON memory_summaries(user_id);
CREATE INDEX IF NOT EXISTS idx_summary_corr ON memory_summaries(correlation_id);

-- Vector index for summary search
CREATE INDEX IF NOT EXISTS idx_summary_vector ON memory_summaries
    USING hnsw (vector vector_cosine_ops)
    WHERE vector IS NOT NULL;


-- =============================================================================
-- TABLE: reflection_store (Persistent Self-Reflection)
-- Purpose: Durable storage for lessons, patterns, failures, successes
-- =============================================================================
CREATE TABLE IF NOT EXISTS reflection_store (
    reflection_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id TEXT,
    reflection_type TEXT NOT NULL CHECK (reflection_type IN ('lesson', 'pattern', 'failure', 'success', 'insight', 'improvement', 'false_constraint')),
    content TEXT NOT NULL,
    context TEXT,
    entities TEXT[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    confidence FLOAT DEFAULT 0.8 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    source_agent TEXT,
    source_packet UUID REFERENCES packet_store(packet_id) ON DELETE SET NULL,
    access_count INT DEFAULT 0,
    last_accessed TIMESTAMPTZ,
    vector VECTOR(1536),                    -- For semantic search of reflections
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    -- Multi-tenant identity (4 core fields)
    tenant_id UUID,
    org_id UUID,
    user_id UUID,
    correlation_id UUID DEFAULT uuid_generate_v4(),
    -- Tracing
    session_id TEXT,
    trace_id TEXT
);

COMMENT ON TABLE reflection_store IS 'Persistent storage for agent reflections and lessons learned';
COMMENT ON COLUMN reflection_store.reflection_type IS 'Type: lesson, pattern, failure, success, insight, improvement, false_constraint';

CREATE INDEX IF NOT EXISTS idx_reflection_task ON reflection_store(task_id);
CREATE INDEX IF NOT EXISTS idx_reflection_type ON reflection_store(reflection_type);
CREATE INDEX IF NOT EXISTS idx_reflection_priority ON reflection_store(priority);
CREATE INDEX IF NOT EXISTS idx_reflection_agent ON reflection_store(source_agent);
CREATE INDEX IF NOT EXISTS idx_reflection_entities ON reflection_store USING GIN(entities);
CREATE INDEX IF NOT EXISTS idx_reflection_tags ON reflection_store USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_reflection_created ON reflection_store(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reflection_confidence ON reflection_store(confidence DESC);

-- Multi-tenant indexes for reflection_store
CREATE INDEX IF NOT EXISTS idx_reflection_tenant ON reflection_store(tenant_id);
CREATE INDEX IF NOT EXISTS idx_reflection_org ON reflection_store(org_id);
CREATE INDEX IF NOT EXISTS idx_reflection_user ON reflection_store(user_id);
CREATE INDEX IF NOT EXISTS idx_reflection_corr ON reflection_store(correlation_id);

-- Vector index for semantic reflection search
CREATE INDEX IF NOT EXISTS idx_reflection_vector ON reflection_store
    USING hnsw (vector vector_cosine_ops)
    WHERE vector IS NOT NULL;


-- =============================================================================
-- TABLE: task_reflections (Task-Scoped Learning)
-- Purpose: Structured reflections per task for outcome analysis
-- =============================================================================
CREATE TABLE IF NOT EXISTS task_reflections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id TEXT NOT NULL UNIQUE,
    task_description TEXT,
    outcome TEXT DEFAULT 'unknown' CHECK (outcome IN ('success', 'partial', 'failure', 'unknown', 'cancelled')),
    what_worked TEXT[] DEFAULT '{}',
    what_failed TEXT[] DEFAULT '{}',
    false_constraints TEXT[] DEFAULT '{}',
    helpful_patterns TEXT[] DEFAULT '{}',
    lessons TEXT[] DEFAULT '{}',
    recommendations TEXT[] DEFAULT '{}',
    related_decisions UUID[] DEFAULT '{}',  -- Links to decision packets
    execution_time_ms FLOAT,
    metrics_improved JSONB DEFAULT '{}',
    metrics_degraded JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    -- Multi-tenant identity (4 core fields)
    tenant_id UUID,
    org_id UUID,
    user_id UUID,
    correlation_id UUID DEFAULT uuid_generate_v4()
);

COMMENT ON TABLE task_reflections IS 'Structured per-task reflection data for learning';
COMMENT ON COLUMN task_reflections.false_constraints IS 'Constraints that turned out to be unnecessary';

CREATE INDEX IF NOT EXISTS idx_task_refl_outcome ON task_reflections(outcome);
CREATE INDEX IF NOT EXISTS idx_task_refl_patterns ON task_reflections USING GIN(helpful_patterns);
CREATE INDEX IF NOT EXISTS idx_task_refl_created ON task_reflections(created_at DESC);

-- Multi-tenant indexes for task_reflections
CREATE INDEX IF NOT EXISTS idx_task_refl_tenant ON task_reflections(tenant_id);
CREATE INDEX IF NOT EXISTS idx_task_refl_org ON task_reflections(org_id);
CREATE INDEX IF NOT EXISTS idx_task_refl_user ON task_reflections(user_id);
CREATE INDEX IF NOT EXISTS idx_task_refl_corr ON task_reflections(correlation_id);


-- =============================================================================
-- ALTER TABLE: packet_store (10X Enhancements + Multi-Tenant)
-- Purpose: Add scope, importance, access tracking, confidence decay, multi-tenant
-- =============================================================================

-- Scope for memory isolation (Cursor vs L vs shared)
ALTER TABLE packet_store ADD COLUMN IF NOT EXISTS scope TEXT DEFAULT 'shared';

-- Importance scoring (0.0-1.0, updated based on access patterns)
ALTER TABLE packet_store ADD COLUMN IF NOT EXISTS importance_score FLOAT DEFAULT 0.5;

-- Access tracking
ALTER TABLE packet_store ADD COLUMN IF NOT EXISTS access_count INT DEFAULT 0;
ALTER TABLE packet_store ADD COLUMN IF NOT EXISTS last_accessed TIMESTAMPTZ;

-- Confidence decay tracking
ALTER TABLE packet_store ADD COLUMN IF NOT EXISTS confidence_updated_at TIMESTAMPTZ;
ALTER TABLE packet_store ADD COLUMN IF NOT EXISTS contradiction_count INT DEFAULT 0;

-- Chunking metadata
ALTER TABLE packet_store ADD COLUMN IF NOT EXISTS chunk_count INT DEFAULT 1;
ALTER TABLE packet_store ADD COLUMN IF NOT EXISTS is_chunked BOOLEAN DEFAULT FALSE;

-- Content hash for deduplication
ALTER TABLE packet_store ADD COLUMN IF NOT EXISTS content_hash TEXT;

-- Processing status
ALTER TABLE packet_store ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'complete';

-- Multi-tenant identity (4 core fields)
ALTER TABLE packet_store ADD COLUMN IF NOT EXISTS tenant_id UUID;
ALTER TABLE packet_store ADD COLUMN IF NOT EXISTS org_id UUID;
ALTER TABLE packet_store ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE packet_store ADD COLUMN IF NOT EXISTS correlation_id UUID DEFAULT uuid_generate_v4();

-- Tracing columns
ALTER TABLE packet_store ADD COLUMN IF NOT EXISTS session_id TEXT;
ALTER TABLE packet_store ADD COLUMN IF NOT EXISTS trace_id TEXT;

-- Scope-based indexes
CREATE INDEX IF NOT EXISTS idx_packet_scope ON packet_store(scope);
CREATE INDEX IF NOT EXISTS idx_packet_scope_type ON packet_store(scope, packet_type);
CREATE INDEX IF NOT EXISTS idx_packet_scope_time ON packet_store(scope, timestamp DESC);

-- Importance-based retrieval
CREATE INDEX IF NOT EXISTS idx_packet_importance ON packet_store(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_packet_importance_type ON packet_store(packet_type, importance_score DESC);

-- Access-based retrieval
CREATE INDEX IF NOT EXISTS idx_packet_accessed ON packet_store(last_accessed DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_packet_access_count ON packet_store(access_count DESC);

-- Deduplication index
CREATE UNIQUE INDEX IF NOT EXISTS idx_packet_content_hash ON packet_store(content_hash)
    WHERE content_hash IS NOT NULL;

-- Multi-tenant indexes
CREATE INDEX IF NOT EXISTS idx_packet_tenant_ts ON packet_store(tenant_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_packet_org_ts ON packet_store(org_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_packet_user_ts ON packet_store(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_packet_corr ON packet_store(correlation_id);

COMMENT ON COLUMN packet_store.scope IS 'Memory scope: shared, cursor, l-private';
COMMENT ON COLUMN packet_store.importance_score IS 'Learned importance (0.0-1.0), updated via access patterns';
COMMENT ON COLUMN packet_store.contradiction_count IS 'Number of times content was contradicted';
COMMENT ON COLUMN packet_store.tenant_id IS 'Multi-tenant: top-level tenant isolation';
COMMENT ON COLUMN packet_store.org_id IS 'Multi-tenant: organization within tenant';
COMMENT ON COLUMN packet_store.user_id IS 'Multi-tenant: user within organization';
COMMENT ON COLUMN packet_store.correlation_id IS 'Request/session correlation for tracing';


-- =============================================================================
-- ALTER TABLE: knowledge_facts (Graph-Ready + Multi-Tenant)
-- Purpose: Add entity normalization, confidence decay, access tracking, multi-tenant
-- =============================================================================

-- Entity normalization for consistent graph traversal
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS subject_normalized TEXT;
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS object_normalized TEXT;

-- Object type for polymorphic objects
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS object_type TEXT DEFAULT 'value';

-- Confidence decay tracking
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS confidence_updated_at TIMESTAMPTZ;
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS contradiction_count INT DEFAULT 0;
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS supporting_packet_count INT DEFAULT 1;

-- Access tracking
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS access_count INT DEFAULT 0;
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS last_accessed TIMESTAMPTZ;

-- Scope
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS scope TEXT DEFAULT 'shared';

-- Multi-tenant identity (4 core fields)
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS tenant_id UUID;
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS org_id UUID;
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE knowledge_facts ADD COLUMN IF NOT EXISTS correlation_id UUID DEFAULT uuid_generate_v4();

-- Graph traversal indexes
CREATE INDEX IF NOT EXISTS idx_facts_subject_norm ON knowledge_facts(subject_normalized);
CREATE INDEX IF NOT EXISTS idx_facts_object_norm ON knowledge_facts(object_normalized);
CREATE INDEX IF NOT EXISTS idx_facts_scope ON knowledge_facts(scope);

-- Confidence-weighted retrieval
CREATE INDEX IF NOT EXISTS idx_facts_confidence_desc ON knowledge_facts(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_facts_access ON knowledge_facts(last_accessed DESC NULLS LAST);

-- Multi-tenant indexes
CREATE INDEX IF NOT EXISTS idx_facts_tenant_ts ON knowledge_facts(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_facts_org_ts ON knowledge_facts(org_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_facts_user_ts ON knowledge_facts(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_facts_corr ON knowledge_facts(correlation_id);

COMMENT ON COLUMN knowledge_facts.subject_normalized IS 'Normalized entity name for consistent lookup';
COMMENT ON COLUMN knowledge_facts.supporting_packet_count IS 'Number of packets supporting this fact';
COMMENT ON COLUMN knowledge_facts.tenant_id IS 'Multi-tenant: top-level tenant isolation';
COMMENT ON COLUMN knowledge_facts.org_id IS 'Multi-tenant: organization within tenant';


-- =============================================================================
-- ALTER TABLE: semantic_memory (Legacy Enhancement + Multi-Tenant)
-- Purpose: Add importance, access tracking, multi-tenant to legacy semantic table
-- =============================================================================

ALTER TABLE semantic_memory ADD COLUMN IF NOT EXISTS importance_score FLOAT DEFAULT 0.5;
ALTER TABLE semantic_memory ADD COLUMN IF NOT EXISTS access_count INT DEFAULT 0;
ALTER TABLE semantic_memory ADD COLUMN IF NOT EXISTS last_accessed TIMESTAMPTZ;
ALTER TABLE semantic_memory ADD COLUMN IF NOT EXISTS embedding_type TEXT DEFAULT 'content';
ALTER TABLE semantic_memory ADD COLUMN IF NOT EXISTS scope TEXT DEFAULT 'shared';

-- Multi-tenant identity (4 core fields)
ALTER TABLE semantic_memory ADD COLUMN IF NOT EXISTS tenant_id UUID;
ALTER TABLE semantic_memory ADD COLUMN IF NOT EXISTS org_id UUID;
ALTER TABLE semantic_memory ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE semantic_memory ADD COLUMN IF NOT EXISTS correlation_id UUID DEFAULT uuid_generate_v4();

CREATE INDEX IF NOT EXISTS idx_semantic_importance ON semantic_memory(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_semantic_scope ON semantic_memory(scope);

-- Multi-tenant indexes
CREATE INDEX IF NOT EXISTS idx_semantic_tenant ON semantic_memory(tenant_id);
CREATE INDEX IF NOT EXISTS idx_semantic_org ON semantic_memory(org_id);
CREATE INDEX IF NOT EXISTS idx_semantic_user ON semantic_memory(user_id);


-- =============================================================================
-- FUNCTIONS: Memory Operations
-- =============================================================================

-- Function: Update packet access (call on every retrieval)
CREATE OR REPLACE FUNCTION update_packet_access(p_id UUID, accessing_agent TEXT DEFAULT 'system')
RETURNS VOID AS $$
BEGIN
    UPDATE packet_store
    SET
        access_count = access_count + 1,
        last_accessed = NOW(),
        importance_score = LEAST(1.0, importance_score + 0.02)
    WHERE packet_id = p_id;

    INSERT INTO memory_access_log (target_type, target_id, agent_id, accessed_at)
    VALUES ('packet', p_id, accessing_agent, NOW());
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_packet_access IS 'Track packet access and boost importance';


-- Function: Decay confidence for contradicted facts
CREATE OR REPLACE FUNCTION decay_fact_confidence(f_id UUID, decay_factor FLOAT DEFAULT 0.1)
RETURNS FLOAT AS $$
DECLARE
    new_confidence FLOAT;
BEGIN
    UPDATE knowledge_facts
    SET
        confidence = GREATEST(0.1, confidence - decay_factor),
        contradiction_count = contradiction_count + 1,
        confidence_updated_at = NOW()
    WHERE fact_id = f_id
    RETURNING confidence INTO new_confidence;

    RETURN new_confidence;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION decay_fact_confidence IS 'Decay confidence when fact is contradicted';


-- Function: Reinforce fact confidence
CREATE OR REPLACE FUNCTION reinforce_fact_confidence(f_id UUID, reinforce_factor FLOAT DEFAULT 0.05)
RETURNS FLOAT AS $$
DECLARE
    new_confidence FLOAT;
BEGIN
    UPDATE knowledge_facts
    SET
        confidence = LEAST(1.0, confidence + reinforce_factor),
        supporting_packet_count = supporting_packet_count + 1,
        confidence_updated_at = NOW()
    WHERE fact_id = f_id
    RETURNING confidence INTO new_confidence;

    RETURN new_confidence;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION reinforce_fact_confidence IS 'Reinforce confidence when fact is supported';


-- Function: Temporal importance weight (exponential decay)
CREATE OR REPLACE FUNCTION temporal_weight(ts TIMESTAMPTZ, half_life_days INT DEFAULT 30)
RETURNS FLOAT AS $$
BEGIN
    RETURN POWER(0.5, EXTRACT(EPOCH FROM (NOW() - ts)) / (half_life_days * 86400));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION temporal_weight IS 'Calculate temporal decay weight for aging memories';


-- Function: Combined importance score (access + recency + base importance)
CREATE OR REPLACE FUNCTION combined_importance(
    base_importance FLOAT,
    access_count_val INT,
    last_access TIMESTAMPTZ,
    created_ts TIMESTAMPTZ,
    recency_weight FLOAT DEFAULT 0.3,
    access_weight FLOAT DEFAULT 0.3,
    base_weight FLOAT DEFAULT 0.4
)
RETURNS FLOAT AS $$
DECLARE
    recency_score FLOAT;
    access_score FLOAT;
BEGIN
    -- Recency based on last access or creation
    recency_score := temporal_weight(COALESCE(last_access, created_ts), 30);

    -- Access score (logarithmic to prevent runaway)
    access_score := LEAST(1.0, LOG(access_count_val + 1) / LOG(100));

    RETURN (base_weight * base_importance) +
           (recency_weight * recency_score) +
           (access_weight * access_score);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION combined_importance IS 'Calculate combined importance score for ranking';


-- Function: Normalize entity name
CREATE OR REPLACE FUNCTION normalize_entity(entity_name TEXT)
RETURNS TEXT AS $$
BEGIN
    -- Lowercase, trim, collapse whitespace
    RETURN LOWER(TRIM(REGEXP_REPLACE(entity_name, '\s+', ' ', 'g')));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION normalize_entity IS 'Normalize entity names for consistent lookup';


-- Function: Upsert entity relationship (reinforces existing)
CREATE OR REPLACE FUNCTION upsert_entity_relationship(
    p_source TEXT,
    p_type TEXT,
    p_target TEXT,
    p_confidence FLOAT DEFAULT 0.8,
    p_packet_id UUID DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    rel_id UUID;
BEGIN
    INSERT INTO entity_relationships (source_entity, relationship_type, target_entity, confidence, source_packet)
    VALUES (p_source, p_type, p_target, p_confidence, p_packet_id)
    ON CONFLICT (source_entity, relationship_type, target_entity)
    DO UPDATE SET
        mention_count = entity_relationships.mention_count + 1,
        confidence = LEAST(1.0, entity_relationships.confidence + 0.02),
        last_seen = NOW()
    RETURNING relationship_id INTO rel_id;

    RETURN rel_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION upsert_entity_relationship IS 'Insert or reinforce entity relationship';


-- =============================================================================
-- MATERIALIZED VIEWS: Fast Retrieval Patterns
-- =============================================================================

-- Recent high-importance memories per agent (refresh daily)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_agent_recent_important AS
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

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_agent_recent ON mv_agent_recent_important(agent_id, packet_id);
CREATE INDEX IF NOT EXISTS idx_mv_agent_score ON mv_agent_recent_important(agent_id, combined_score DESC);


-- Entity relationship graph summary (refresh daily)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_entity_graph AS
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

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_entity_unique ON mv_entity_graph(source_entity, relationship_type, target_entity);
CREATE INDEX IF NOT EXISTS idx_mv_entity_source ON mv_entity_graph(source_entity);
CREATE INDEX IF NOT EXISTS idx_mv_entity_target ON mv_entity_graph(target_entity);
CREATE INDEX IF NOT EXISTS idx_mv_entity_mentions ON mv_entity_graph(total_mentions DESC);


-- High-confidence facts summary (refresh daily)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_high_confidence_facts AS
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

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_facts_id ON mv_high_confidence_facts(fact_id);
CREATE INDEX IF NOT EXISTS idx_mv_facts_subject ON mv_high_confidence_facts(subject_normalized);
CREATE INDEX IF NOT EXISTS idx_mv_facts_score ON mv_high_confidence_facts(combined_score DESC);


-- Reflection patterns summary (refresh daily)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_reflection_patterns AS
SELECT
    reflection_type,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence,
    ARRAY_AGG(DISTINCT unnested_tag) as all_tags,
    MAX(created_at) as latest
FROM reflection_store,
     LATERAL unnest(tags) as unnested_tag
GROUP BY reflection_type;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_refl_type ON mv_reflection_patterns(reflection_type);


-- =============================================================================
-- TRIGGERS: Automatic Maintenance
-- =============================================================================

-- Trigger: Auto-normalize entities on knowledge_facts insert/update
CREATE OR REPLACE FUNCTION trigger_normalize_fact_entities()
RETURNS TRIGGER AS $$
BEGIN
    NEW.subject_normalized := normalize_entity(NEW.subject);
    IF NEW.object_type = 'entity' AND NEW.object IS NOT NULL THEN
        NEW.object_normalized := normalize_entity(NEW.object::text);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_normalize_facts ON knowledge_facts;
CREATE TRIGGER trg_normalize_facts
    BEFORE INSERT OR UPDATE ON knowledge_facts
    FOR EACH ROW
    EXECUTE FUNCTION trigger_normalize_fact_entities();


-- Trigger: Auto-update task_reflections.updated_at
CREATE OR REPLACE FUNCTION trigger_update_task_reflection_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_task_refl_updated ON task_reflections;
CREATE TRIGGER trg_task_refl_updated
    BEFORE UPDATE ON task_reflections
    FOR EACH ROW
    EXECUTE FUNCTION trigger_update_task_reflection_timestamp();


-- =============================================================================
-- SCHEDULED JOBS: Memory Maintenance (run via pg_cron or external scheduler)
-- =============================================================================

-- Procedure: Decay importance of unaccessed packets
CREATE OR REPLACE PROCEDURE decay_unaccessed_importance(days_threshold INT DEFAULT 30, decay_rate FLOAT DEFAULT 0.1)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE packet_store
    SET importance_score = GREATEST(0.1, importance_score - decay_rate)
    WHERE last_accessed IS NULL
       OR last_accessed < NOW() - (days_threshold || ' days')::INTERVAL;

    RAISE NOTICE 'Decayed importance for unaccessed packets older than % days', days_threshold;
END;
$$;


-- Procedure: Refresh materialized views
CREATE OR REPLACE PROCEDURE refresh_memory_views()
LANGUAGE plpgsql AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_agent_recent_important;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_entity_graph;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_high_confidence_facts;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_reflection_patterns;

    RAISE NOTICE 'Refreshed all memory materialized views';
END;
$$;


-- Procedure: Clean up expired TTL packets
CREATE OR REPLACE PROCEDURE evict_expired_packets()
LANGUAGE plpgsql AS $$
DECLARE
    evicted_count INT;
BEGIN
    DELETE FROM packet_store
    WHERE ttl IS NOT NULL AND ttl < NOW();

    GET DIAGNOSTICS evicted_count = ROW_COUNT;
    RAISE NOTICE 'Evicted % expired packets', evicted_count;
END;
$$;


-- Procedure: Clean up expired reflections
CREATE OR REPLACE PROCEDURE evict_expired_reflections()
LANGUAGE plpgsql AS $$
DECLARE
    evicted_count INT;
BEGIN
    DELETE FROM reflection_store
    WHERE expires_at IS NOT NULL AND expires_at < NOW();

    GET DIAGNOSTICS evicted_count = ROW_COUNT;
    RAISE NOTICE 'Evicted % expired reflections', evicted_count;
END;
$$;


-- =============================================================================
-- ROW LEVEL SECURITY: Multi-Tenant Memory Isolation
-- Uses session variables: app.tenant_id, app.org_id, app.user_id, app.role
-- Roles: platform_admin, tenant_admin, org_admin, end_user
-- =============================================================================

-- Create roles if not exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cursor_user') THEN
        CREATE ROLE cursor_user;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'l9_user') THEN
        CREATE ROLE l9_user;
    END IF;
END
$$;

-- =============================================================================
-- Multi-Tenant RLS Policies (using session variables)
-- Applied to all memory tables
-- =============================================================================

DO $$
DECLARE
    t text;
    tables text[] := ARRAY[
        'packet_store',
        'semantic_memory',
        'knowledge_facts',
        'memory_embeddings',
        'memory_access_log',
        'entity_relationships',
        'memory_summaries',
        'reflection_store',
        'task_reflections'
    ];
BEGIN
    FOREACH t IN ARRAY tables LOOP
        -- Enable RLS and force it (even for table owners)
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);

        -- ============================================================
        -- Policy 1: Tenant Isolation
        -- Users can only see rows matching their tenant_id
        -- ============================================================
        EXECUTE format($pol$
            DROP POLICY IF EXISTS %I_tenant_isolation ON %I;
            CREATE POLICY %I_tenant_isolation ON %I
            FOR ALL
            USING (
                tenant_id IS NULL
                OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            )
            WITH CHECK (
                tenant_id IS NULL
                OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            );
        $pol$, t, t, t, t);

        -- ============================================================
        -- Policy 2: Organization Isolation
        -- Within tenant, users can only see rows matching their org_id
        -- ============================================================
        EXECUTE format($pol$
            DROP POLICY IF EXISTS %I_org_isolation ON %I;
            CREATE POLICY %I_org_isolation ON %I
            FOR ALL
            USING (
                org_id IS NULL
                OR org_id = NULLIF(current_setting('app.org_id', true), '')::uuid
            )
            WITH CHECK (
                org_id IS NULL
                OR org_id = NULLIF(current_setting('app.org_id', true), '')::uuid
            );
        $pol$, t, t, t, t);

        -- ============================================================
        -- Policy 3: Admin Override
        -- Platform admins and tenant admins can see all rows
        -- ============================================================
        EXECUTE format($pol$
            DROP POLICY IF EXISTS %I_admin_override ON %I;
            CREATE POLICY %I_admin_override ON %I
            FOR ALL
            USING (
                COALESCE(current_setting('app.role', true), 'end_user') IN ('platform_admin', 'tenant_admin')
            )
            WITH CHECK (
                COALESCE(current_setting('app.role', true), 'end_user') IN ('platform_admin', 'tenant_admin')
            );
        $pol$, t, t, t, t);

        -- ============================================================
        -- Policy 4: User Visibility (for end_user role)
        -- End users can only see their own rows or rows with null user_id
        -- ============================================================
        EXECUTE format($pol$
            DROP POLICY IF EXISTS %I_user_visibility ON %I;
            CREATE POLICY %I_user_visibility ON %I
            FOR ALL
            USING (
                COALESCE(current_setting('app.role', true), 'end_user') <> 'end_user'
                OR user_id IS NULL
                OR user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
            )
            WITH CHECK (
                COALESCE(current_setting('app.role', true), 'end_user') <> 'end_user'
                OR user_id IS NULL
                OR user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
            );
        $pol$, t, t, t, t);

    END LOOP;
END$$;

-- =============================================================================
-- Additional Scope-Based Policies for Legacy Compatibility
-- These work alongside multi-tenant for the scope column (shared/cursor/l-private)
-- =============================================================================

-- packet_store scope policy
DROP POLICY IF EXISTS packet_store_scope_access ON packet_store;
CREATE POLICY packet_store_scope_access ON packet_store
    FOR ALL
    USING (
        scope IS NULL
        OR scope = 'shared'
        OR (scope = 'cursor' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('cursor_user', 'platform_admin', 'tenant_admin'))
        OR (scope = 'l-private' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('l9_system', 'platform_admin'))
    )
    WITH CHECK (
        scope IS NULL
        OR scope = 'shared'
        OR (scope = 'cursor' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('cursor_user', 'platform_admin', 'tenant_admin'))
        OR (scope = 'l-private' AND COALESCE(current_setting('app.role', true), 'end_user') IN ('l9_system', 'platform_admin'))
    );

-- knowledge_facts scope policy
DROP POLICY IF EXISTS knowledge_facts_scope_access ON knowledge_facts;
CREATE POLICY knowledge_facts_scope_access ON knowledge_facts
    FOR ALL
    USING (
        scope IS NULL
        OR scope = 'shared'
        OR COALESCE(current_setting('app.role', true), 'end_user') IN ('platform_admin', 'tenant_admin', 'l9_system')
    )
    WITH CHECK (
        scope IS NULL
        OR scope = 'shared'
        OR COALESCE(current_setting('app.role', true), 'end_user') IN ('platform_admin', 'tenant_admin', 'l9_system')
    );

-- semantic_memory scope policy
DROP POLICY IF EXISTS semantic_memory_scope_access ON semantic_memory;
CREATE POLICY semantic_memory_scope_access ON semantic_memory
    FOR ALL
    USING (
        scope IS NULL
        OR scope = 'shared'
        OR COALESCE(current_setting('app.role', true), 'end_user') IN ('platform_admin', 'tenant_admin', 'l9_system')
    )
    WITH CHECK (
        scope IS NULL
        OR scope = 'shared'
        OR COALESCE(current_setting('app.role', true), 'end_user') IN ('platform_admin', 'tenant_admin', 'l9_system')
    );


-- =============================================================================
-- COMMENTS: Documentation
-- =============================================================================

COMMENT ON TABLE memory_embeddings IS 'Multi-space vector embeddings (content, context, entity, summary, reasoning) for precision retrieval';
COMMENT ON TABLE memory_access_log IS 'Access tracking for importance learning and relevance feedback';
COMMENT ON TABLE entity_relationships IS 'Knowledge graph edges for entity-to-entity traversal';
COMMENT ON TABLE memory_summaries IS 'Consolidated summaries for long-term memory efficiency';
COMMENT ON TABLE reflection_store IS 'Persistent reflections: lessons, patterns, failures, successes';
COMMENT ON TABLE task_reflections IS 'Structured per-task reflection for outcome-based learning';

COMMENT ON FUNCTION update_packet_access IS 'Call on every packet retrieval to track access and boost importance';
COMMENT ON FUNCTION decay_fact_confidence IS 'Decay fact confidence when contradicted';
COMMENT ON FUNCTION reinforce_fact_confidence IS 'Reinforce fact confidence when supported';
COMMENT ON FUNCTION temporal_weight IS 'Calculate exponential decay weight (default 30-day half-life)';
COMMENT ON FUNCTION combined_importance IS 'Calculate ranking score combining access, recency, base importance';
COMMENT ON FUNCTION normalize_entity IS 'Normalize entity names for consistent graph lookup';
COMMENT ON FUNCTION upsert_entity_relationship IS 'Insert or reinforce entity relationship (uses UPSERT)';


-- =============================================================================
-- MIGRATION COMPLETE
-- =============================================================================

-- Verify tables exist and multi-tenant columns added
DO $$
DECLARE
    table_count INT;
    tenant_col_count INT;
BEGIN
    -- Check new tables
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name IN (
          'memory_embeddings',
          'memory_access_log',
          'entity_relationships',
          'memory_summaries',
          'reflection_store',
          'task_reflections'
      );

    -- Check multi-tenant columns on packet_store
    SELECT COUNT(*) INTO tenant_col_count
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'packet_store'
      AND column_name IN ('tenant_id', 'org_id', 'user_id', 'correlation_id');

    IF table_count = 6 AND tenant_col_count = 4 THEN
        RAISE NOTICE '✅ Migration 0008_memory_substrate_10x.sql completed successfully';
        RAISE NOTICE '   - 6 new tables created';
        RAISE NOTICE '   - Multi-tenant columns (tenant_id, org_id, user_id, correlation_id) added';
        RAISE NOTICE '   - packet_store enhanced with scope, importance, access tracking';
        RAISE NOTICE '   - knowledge_facts enhanced with normalization and confidence decay';
        RAISE NOTICE '   - Row Level Security enabled with 4 policies per table';
        RAISE NOTICE '   - Materialized views created for fast retrieval';
        RAISE NOTICE '   - Maintenance procedures created for scheduled jobs';
        RAISE NOTICE '   - Session variable functions: l9_set_scope(), l9_current_tenant(), etc.';
    ELSE
        RAISE WARNING '⚠️ Migration may be incomplete. Tables: %/6, Tenant columns: %/4', table_count, tenant_col_count;
    END IF;
END
$$;

COMMIT;

-- =============================================================================
-- POST-MIGRATION: How to Use Multi-Tenant Features
-- =============================================================================
--
-- 1. Set session scope before queries:
--    SELECT l9_set_scope(
--        'tenant-uuid'::uuid,
--        'org-uuid'::uuid,
--        'user-uuid'::uuid,
--        'end_user'  -- or 'org_admin', 'tenant_admin', 'platform_admin'
--    );
--
-- 2. All queries will automatically filter by tenant/org/user via RLS
--
-- 3. For admin access (bypass RLS):
--    SELECT l9_set_scope(tenant_uuid, org_uuid, user_uuid, 'platform_admin');
--
-- 4. Check current context:
--    SELECT l9_current_tenant(), l9_current_org(), l9_current_user_id(), l9_current_role();
--
-- 5. Backfill existing data (run separately, adjust UUIDs):
--    UPDATE packet_store SET
--        tenant_id = 'default-tenant-uuid'::uuid,
--        org_id = 'default-org-uuid'::uuid,
--        user_id = 'default-user-uuid'::uuid
--    WHERE tenant_id IS NULL;
--
-- =============================================================================
-- END MIGRATION 0008
-- =============================================================================
