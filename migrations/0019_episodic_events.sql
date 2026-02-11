-- =============================================================================
-- L9 Memory Substrate - Migration 0019
-- Version: 3.1.0
-- Purpose: Create episodic_events and episodic_semantic_links tables
-- =============================================================================
-- Stores temporal events with linked semantic facts for frontier-grade
-- dual semantic+episodic memory architecture.
-- Apply AFTER 0018_semantic_facts.sql
-- =============================================================================

-- =============================================================================
-- TABLE: episodic_events
-- Type: Episodic Memory (Events)
-- Purpose: Store temporal events with timestamps and entity references
-- =============================================================================
CREATE TABLE IF NOT EXISTS episodic_events (
    -- Primary key
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Ownership (multi-tenant)
    tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'::uuid,
    org_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'::uuid,
    user_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'::uuid,
    agent_id TEXT,  -- Which agent observed this event

    -- Event content
    observation TEXT NOT NULL,  -- What happened (human-readable description)
    event_type TEXT DEFAULT 'general',  -- Type categorization

    -- Temporal information (CRITICAL for episodic memory)
    event_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,  -- When the event occurred
    duration_seconds INTEGER,  -- How long the event lasted (if applicable)

    -- Entity references (for linking to semantic facts)
    entities TEXT[] DEFAULT '{}',  -- Entities involved (names, IDs, concepts)

    -- Context and outcome
    context JSONB DEFAULT '{}'::jsonb,  -- Additional context (location, task, etc.)
    outcome TEXT,  -- What was the result/outcome

    -- Importance and ranking
    severity DOUBLE PRECISION DEFAULT 0.5 CHECK (severity >= 0.0 AND severity <= 1.0),
    impact_score DOUBLE PRECISION DEFAULT 0.5 CHECK (impact_score >= 0.0 AND impact_score <= 1.0),

    -- Lineage (optional link to packet that generated this event)
    source_packet_id UUID REFERENCES packet_store(packet_id) ON DELETE SET NULL,
    parent_event_id UUID REFERENCES episodic_events(event_id) ON DELETE SET NULL,

    -- Session/thread grouping
    session_id UUID,  -- Group events by session
    thread_id UUID,  -- Link to packet thread (no FK - thread_id is not unique in packet_store)

    -- Decay and retention
    decay_factor DOUBLE PRECISION DEFAULT 1.0,  -- Starts at 1.0, decays over time
    last_recalled TIMESTAMP WITH TIME ZONE,  -- When was this event last retrieved
    recall_count INTEGER DEFAULT 0,  -- How many times retrieved

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- TABLE: episodic_semantic_links
-- Type: Junction Table
-- Purpose: Link episodic events to semantic facts (many-to-many)
-- =============================================================================
CREATE TABLE IF NOT EXISTS episodic_semantic_links (
    -- Composite primary key
    link_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign keys
    event_id UUID NOT NULL REFERENCES episodic_events(event_id) ON DELETE CASCADE,
    fact_id UUID NOT NULL REFERENCES semantic_facts(fact_id) ON DELETE CASCADE,

    -- Link metadata
    relationship_type TEXT DEFAULT 'involves',  -- Type of relationship
    strength DOUBLE PRECISION DEFAULT 1.0 CHECK (strength >= 0.0 AND strength <= 1.0),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique constraint (one link per event-fact pair)
    CONSTRAINT uq_episodic_semantic_link UNIQUE (event_id, fact_id)
);

-- =============================================================================
-- INDEXES for episodic_events
-- =============================================================================

-- Primary temporal index (most important for episodic queries)
CREATE INDEX IF NOT EXISTS idx_episodic_events_timestamp
    ON episodic_events (tenant_id, event_timestamp DESC);

-- Entity index for finding events by entity
CREATE INDEX IF NOT EXISTS idx_episodic_events_entities
    ON episodic_events USING GIN (entities);

-- Event type index
CREATE INDEX IF NOT EXISTS idx_episodic_events_type
    ON episodic_events (event_type);

-- Severity index for importance-based retrieval
CREATE INDEX IF NOT EXISTS idx_episodic_events_severity
    ON episodic_events (severity DESC);

-- Session grouping index
CREATE INDEX IF NOT EXISTS idx_episodic_events_session
    ON episodic_events (session_id)
    WHERE session_id IS NOT NULL;

-- Agent index
CREATE INDEX IF NOT EXISTS idx_episodic_events_agent
    ON episodic_events (agent_id)
    WHERE agent_id IS NOT NULL;

-- Parent event index for event chains
CREATE INDEX IF NOT EXISTS idx_episodic_events_parent
    ON episodic_events (parent_event_id)
    WHERE parent_event_id IS NOT NULL;

-- Multi-tenant index
CREATE INDEX IF NOT EXISTS idx_episodic_events_tenant
    ON episodic_events (tenant_id, org_id, user_id);

-- Context GIN index for JSONB queries
CREATE INDEX IF NOT EXISTS idx_episodic_events_context
    ON episodic_events USING GIN (context);

-- =============================================================================
-- INDEXES for episodic_semantic_links
-- =============================================================================

-- Event lookup (find all facts for an event)
CREATE INDEX IF NOT EXISTS idx_episodic_semantic_links_event
    ON episodic_semantic_links (event_id);

-- Fact lookup (find all events for a fact)
CREATE INDEX IF NOT EXISTS idx_episodic_semantic_links_fact
    ON episodic_semantic_links (fact_id);

-- Relationship type index
CREATE INDEX IF NOT EXISTS idx_episodic_semantic_links_type
    ON episodic_semantic_links (relationship_type);

-- =============================================================================
-- TRIGGER: Auto-update updated_at on episodic_events modification
-- =============================================================================
CREATE OR REPLACE FUNCTION update_episodic_events_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_episodic_events_updated_at ON episodic_events;
CREATE TRIGGER trigger_episodic_events_updated_at
    BEFORE UPDATE ON episodic_events
    FOR EACH ROW
    EXECUTE FUNCTION update_episodic_events_updated_at();

-- =============================================================================
-- FUNCTION: Apply temporal decay to episodic events
-- =============================================================================
CREATE OR REPLACE FUNCTION apply_episodic_decay(
    half_life_days DOUBLE PRECISION DEFAULT 30.0
)
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    -- Apply exponential decay based on age
    -- decay_factor = 2^(-age_days / half_life_days)
    UPDATE episodic_events
    SET decay_factor = POWER(2.0, -EXTRACT(EPOCH FROM (NOW() - event_timestamp)) / 86400.0 / half_life_days)
    WHERE decay_factor > 0.01;  -- Don't update nearly-zero values

    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION apply_episodic_decay IS 'Apply temporal decay to episodic events based on half-life';

-- =============================================================================
-- RLS (Row-Level Security) Policies for episodic_events
-- =============================================================================
ALTER TABLE episodic_events ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (idempotent)
DROP POLICY IF EXISTS episodic_events_platform_admin ON episodic_events;
DROP POLICY IF EXISTS episodic_events_tenant_admin ON episodic_events;
DROP POLICY IF EXISTS episodic_events_end_user ON episodic_events;

-- Platform admin: full access
CREATE POLICY episodic_events_platform_admin ON episodic_events
    FOR ALL
    USING (current_setting('app.role', true) = 'platform_admin');

-- Tenant admin: access within tenant
CREATE POLICY episodic_events_tenant_admin ON episodic_events
    FOR ALL
    USING (
        current_setting('app.role', true) = 'tenant_admin'
        AND tenant_id = current_setting('app.tenant_id', true)::uuid
    );

-- End user: access within org
CREATE POLICY episodic_events_end_user ON episodic_events
    FOR ALL
    USING (
        current_setting('app.role', true) IN ('end_user', 'org_admin')
        AND tenant_id = current_setting('app.tenant_id', true)::uuid
        AND org_id = current_setting('app.org_id', true)::uuid
    );

-- =============================================================================
-- RLS Policies for episodic_semantic_links
-- =============================================================================
ALTER TABLE episodic_semantic_links ENABLE ROW LEVEL SECURITY;

-- Links inherit access from events (via join)
CREATE POLICY episodic_semantic_links_access ON episodic_semantic_links
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM episodic_events e
            WHERE e.event_id = episodic_semantic_links.event_id
        )
    );

-- =============================================================================
-- Comments
-- =============================================================================
COMMENT ON TABLE episodic_events IS 'Temporal event storage for episodic memory (Memory Spec v3.1)';
COMMENT ON COLUMN episodic_events.observation IS 'Human-readable description of what happened';
COMMENT ON COLUMN episodic_events.event_timestamp IS 'When the event occurred (CRITICAL for temporal queries)';
COMMENT ON COLUMN episodic_events.entities IS 'Entities involved in this event (for fact linking)';
COMMENT ON COLUMN episodic_events.severity IS 'Event importance 0.0-1.0';
COMMENT ON COLUMN episodic_events.decay_factor IS 'Temporal decay factor, starts at 1.0 and decreases with age';
COMMENT ON COLUMN episodic_events.parent_event_id IS 'Optional parent event for event chains/causality';

COMMENT ON TABLE episodic_semantic_links IS 'Links episodic events to semantic facts (many-to-many)';
COMMENT ON COLUMN episodic_semantic_links.relationship_type IS 'Type of link: involves, confirms, contradicts, updates';
COMMENT ON COLUMN episodic_semantic_links.strength IS 'Link strength 0.0-1.0';

-- =============================================================================
-- End Migration 0019
-- =============================================================================
