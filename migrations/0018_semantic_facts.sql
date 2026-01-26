-- =============================================================================
-- L9 Memory Substrate - Migration 0018
-- Version: 3.1.0
-- Purpose: Create semantic_facts table for frontier-grade fact storage
-- =============================================================================
-- Stores semantic facts with triplets, importance scoring, tags, and embeddings.
-- Supports the dual semantic+episodic memory architecture from frontier AI labs.
-- Apply AFTER 0017_governance_project_id.sql
-- =============================================================================

-- =============================================================================
-- TABLE: semantic_facts
-- Type: Semantic Memory (Facts)
-- Purpose: Store structured facts with importance weighting and embeddings
-- =============================================================================
CREATE TABLE IF NOT EXISTS semantic_facts (
    -- Primary key
    fact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Ownership (multi-tenant)
    tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'::uuid,
    org_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'::uuid,
    user_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'::uuid,
    agent_id TEXT,  -- Which agent created/owns this fact

    -- Fact content
    fact_text TEXT NOT NULL,  -- Human-readable fact statement

    -- Triplet structure (subject-predicate-object)
    triplet JSONB DEFAULT '{}'::jsonb,  -- {"subject": "X", "predicate": "is_a", "object": "Y"}

    -- Embedding for semantic search
    embedding vector(3072),  -- text-embedding-3-large dimensions

    -- Importance and ranking
    importance DOUBLE PRECISION DEFAULT 0.5 CHECK (importance >= 0.0 AND importance <= 1.0),
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE,

    -- Categorization
    tags TEXT[] DEFAULT '{}',
    tier TEXT DEFAULT 'general' CHECK (tier IN ('identity', 'project', 'session', 'general')),

    -- Source tracking
    source TEXT,  -- Where this fact came from (e.g., "user_stated", "inferred", "extracted")
    source_packet_id UUID REFERENCES packet_store(packet_id) ON DELETE SET NULL,

    -- Confidence and validation
    confidence DOUBLE PRECISION DEFAULT 0.8 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    validated_at TIMESTAMP WITH TIME ZONE,
    validated_by TEXT,  -- "igor", "L", "system"

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Uniqueness constraint per tenant (same fact text = same fact)
    CONSTRAINT uq_semantic_facts_tenant_fact UNIQUE (tenant_id, fact_text)
);

-- =============================================================================
-- INDEXES for semantic_facts
-- =============================================================================

-- Embedding index for vector similarity search (IVFFlat for large datasets)
CREATE INDEX IF NOT EXISTS idx_semantic_facts_embedding
    ON semantic_facts USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Triplet component indexes for graph-style queries
CREATE INDEX IF NOT EXISTS idx_semantic_facts_triplet_subject
    ON semantic_facts ((triplet->>'subject'));

CREATE INDEX IF NOT EXISTS idx_semantic_facts_triplet_predicate
    ON semantic_facts ((triplet->>'predicate'));

-- Full triplet GIN index for complex JSON queries
CREATE INDEX IF NOT EXISTS idx_semantic_facts_triplet_gin
    ON semantic_facts USING GIN (triplet);

-- Tags index for filtering
CREATE INDEX IF NOT EXISTS idx_semantic_facts_tags
    ON semantic_facts USING GIN (tags);

-- Tier index for hierarchical queries
CREATE INDEX IF NOT EXISTS idx_semantic_facts_tier
    ON semantic_facts (tier);

-- Importance index for ranking
CREATE INDEX IF NOT EXISTS idx_semantic_facts_importance
    ON semantic_facts (importance DESC);

-- Agent index for per-agent queries
CREATE INDEX IF NOT EXISTS idx_semantic_facts_agent
    ON semantic_facts (agent_id)
    WHERE agent_id IS NOT NULL;

-- Multi-tenant index
CREATE INDEX IF NOT EXISTS idx_semantic_facts_tenant
    ON semantic_facts (tenant_id, org_id, user_id);

-- Created timestamp for recency
CREATE INDEX IF NOT EXISTS idx_semantic_facts_created_at
    ON semantic_facts (created_at DESC);

-- =============================================================================
-- TRIGGER: Auto-update updated_at on modification
-- =============================================================================
CREATE OR REPLACE FUNCTION update_semantic_facts_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_semantic_facts_updated_at ON semantic_facts;
CREATE TRIGGER trigger_semantic_facts_updated_at
    BEFORE UPDATE ON semantic_facts
    FOR EACH ROW
    EXECUTE FUNCTION update_semantic_facts_updated_at();

-- =============================================================================
-- RLS (Row-Level Security) Policies
-- =============================================================================
ALTER TABLE semantic_facts ENABLE ROW LEVEL SECURITY;

-- Platform admin: full access
CREATE POLICY semantic_facts_platform_admin ON semantic_facts
    FOR ALL
    USING (current_setting('app.role', true) = 'platform_admin');

-- Tenant admin: access within tenant
CREATE POLICY semantic_facts_tenant_admin ON semantic_facts
    FOR ALL
    USING (
        current_setting('app.role', true) = 'tenant_admin'
        AND tenant_id = current_setting('app.tenant_id', true)::uuid
    );

-- End user: access within org
CREATE POLICY semantic_facts_end_user ON semantic_facts
    FOR ALL
    USING (
        current_setting('app.role', true) IN ('end_user', 'org_admin')
        AND tenant_id = current_setting('app.tenant_id', true)::uuid
        AND org_id = current_setting('app.org_id', true)::uuid
    );

-- =============================================================================
-- Comments
-- =============================================================================
COMMENT ON TABLE semantic_facts IS 'Frontier-grade semantic facts storage with triplets, importance, and embeddings (Memory Spec v3.1)';
COMMENT ON COLUMN semantic_facts.fact_text IS 'Human-readable fact statement (e.g., "Python is a programming language")';
COMMENT ON COLUMN semantic_facts.triplet IS 'SPO triplet as JSONB: {"subject": "...", "predicate": "...", "object": "..."}';
COMMENT ON COLUMN semantic_facts.importance IS 'Importance score 0.0-1.0, elevated on repeated access or validation';
COMMENT ON COLUMN semantic_facts.tier IS 'Memory tier: identity (core), project (scoped), session (ephemeral), general (default)';
COMMENT ON COLUMN semantic_facts.source IS 'Origin: user_stated, inferred, extracted, imported';
COMMENT ON COLUMN semantic_facts.confidence IS 'Extraction/inference confidence 0.0-1.0';

-- =============================================================================
-- End Migration 0018
-- =============================================================================
