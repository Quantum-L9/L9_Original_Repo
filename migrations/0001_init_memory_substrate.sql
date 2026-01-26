-- =============================================================================
-- L9 Memory Substrate - Initial Migration
-- Version: 1.0.0
-- Schema: plasticos_memory_substrate
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =============================================================================
-- TABLE: agent_memory_events
-- Type: structured
-- Purpose: Store structured agent memory events with packet references
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_memory_events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    packet_id UUID,
    event_type TEXT NOT NULL,
    content JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_memory_events_agent_id ON agent_memory_events(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_memory_events_timestamp ON agent_memory_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_agent_memory_events_event_type ON agent_memory_events(event_type);
CREATE INDEX IF NOT EXISTS idx_agent_memory_events_packet_id ON agent_memory_events(packet_id);

-- =============================================================================
-- TABLE: semantic_memory
-- Type: vector
-- Purpose: Store semantic embeddings with pgvector for similarity search
-- =============================================================================
CREATE TABLE IF NOT EXISTS semantic_memory (
    embedding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id TEXT,
    vector VECTOR(1536) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_semantic_memory_agent_id ON semantic_memory(agent_id);
CREATE INDEX IF NOT EXISTS idx_semantic_memory_created_at ON semantic_memory(created_at DESC);

-- IVFFlat index for approximate nearest neighbor search
-- Note: Run AFTER inserting some data for optimal clustering
-- CREATE INDEX IF NOT EXISTS idx_semantic_memory_vector_ivfflat
--     ON semantic_memory USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);

-- HNSW index (alternative, usually better for smaller datasets)
CREATE INDEX IF NOT EXISTS idx_semantic_memory_vector_hnsw
    ON semantic_memory USING hnsw (vector vector_cosine_ops);

-- =============================================================================
-- TABLE: agent_log
-- Type: structured
-- Purpose: Centralized agent logging with structured metadata
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_log (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    agent_id TEXT NOT NULL,
    level TEXT NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    message TEXT NOT NULL,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_agent_log_agent_id ON agent_log(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_log_timestamp ON agent_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_agent_log_level ON agent_log(level);

-- =============================================================================
-- TABLE: reasoning_traces
-- Type: structured
-- Purpose: Store structured reasoning blocks with inference steps and confidence
-- =============================================================================
CREATE TABLE IF NOT EXISTS reasoning_traces (
    trace_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id TEXT NOT NULL,
    packet_id UUID,
    steps JSONB,
    extracted_features JSONB,
    inference_steps JSONB,
    reasoning_tokens JSONB,
    decision_tokens JSONB,
    confidence_scores JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reasoning_traces_agent_id ON reasoning_traces(agent_id);
CREATE INDEX IF NOT EXISTS idx_reasoning_traces_packet_id ON reasoning_traces(packet_id);
CREATE INDEX IF NOT EXISTS idx_reasoning_traces_created_at ON reasoning_traces(created_at DESC);

-- =============================================================================
-- TABLE: packet_store
-- Type: structured
-- Purpose: Central store for all PacketEnvelopes with routing and provenance
-- =============================================================================
CREATE TABLE IF NOT EXISTS packet_store (
    packet_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    packet_type TEXT NOT NULL,
    envelope JSONB NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    routing JSONB,
    provenance JSONB
);

CREATE INDEX IF NOT EXISTS idx_packet_store_packet_type ON packet_store(packet_type);
CREATE INDEX IF NOT EXISTS idx_packet_store_timestamp ON packet_store(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_packet_store_type_timestamp ON packet_store(packet_type, timestamp DESC);

-- =============================================================================
-- TABLE: graph_checkpoints
-- Type: structured
-- Purpose: LangGraph state checkpoints for agent recovery and debugging
-- =============================================================================
CREATE TABLE IF NOT EXISTS graph_checkpoints (
    checkpoint_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id TEXT NOT NULL UNIQUE,  -- UNIQUE for ON CONFLICT upsert in substrate_repository.py
    graph_state JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_graph_checkpoints_agent_id ON graph_checkpoints(agent_id);
CREATE INDEX IF NOT EXISTS idx_graph_checkpoints_updated_at ON graph_checkpoints(updated_at DESC);

-- =============================================================================
-- TABLE: buyer_profiles
-- Type: structured
-- Purpose: Buyer entity profiles for plastic brokerage domain
-- =============================================================================
CREATE TABLE IF NOT EXISTS buyer_profiles (
    buyer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    profile JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_buyer_profiles_name ON buyer_profiles(name);
CREATE INDEX IF NOT EXISTS idx_buyer_profiles_updated_at ON buyer_profiles(updated_at DESC);

-- =============================================================================
-- TABLE: supplier_profiles
-- Type: structured
-- Purpose: Supplier entity profiles for plastic brokerage domain
-- =============================================================================
CREATE TABLE IF NOT EXISTS supplier_profiles (
    supplier_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    profile JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_supplier_profiles_name ON supplier_profiles(name);
CREATE INDEX IF NOT EXISTS idx_supplier_profiles_updated_at ON supplier_profiles(updated_at DESC);

-- =============================================================================
-- TABLE: transactions
-- Type: structured
-- Purpose: Material transaction records between suppliers and buyers
-- =============================================================================
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    supplier_id UUID REFERENCES supplier_profiles(supplier_id) ON DELETE SET NULL,
    buyer_id UUID REFERENCES buyer_profiles(buyer_id) ON DELETE SET NULL,
    material JSONB NOT NULL,
    price NUMERIC,
    quantity NUMERIC,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_supplier_id ON transactions(supplier_id);
CREATE INDEX IF NOT EXISTS idx_transactions_buyer_id ON transactions(buyer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp DESC);

-- =============================================================================
-- TABLE: material_edges
-- Type: structured
-- Purpose: Material relationship graph edges for knowledge graph integration
-- =============================================================================
CREATE TABLE IF NOT EXISTS material_edges (
    edge_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    material JSONB NOT NULL,
    attributes JSONB,
    relationships JSONB,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_material_edges_updated_at ON material_edges(updated_at DESC);

-- =============================================================================
-- TABLE: entity_metadata
-- Type: structured
-- Purpose: Generic entity metadata store for extensible domain objects
-- =============================================================================
CREATE TABLE IF NOT EXISTS entity_metadata (
    entity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type TEXT NOT NULL,
    metadata JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entity_metadata_entity_type ON entity_metadata(entity_type);
CREATE INDEX IF NOT EXISTS idx_entity_metadata_updated_at ON entity_metadata(updated_at DESC);

-- =============================================================================
-- GRANTS (adjust role names as needed for your deployment)
-- =============================================================================
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO l9_api;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO l9_api;

-- =============================================================================
-- COMMENTS
-- =============================================================================
COMMENT ON TABLE agent_memory_events IS 'Structured agent memory events with packet references';
COMMENT ON TABLE semantic_memory IS 'Vector embeddings for semantic search via pgvector';
COMMENT ON TABLE agent_log IS 'Centralized agent logging';
COMMENT ON TABLE reasoning_traces IS 'Structured reasoning blocks and inference traces';
COMMENT ON TABLE packet_store IS 'Central PacketEnvelope store';
COMMENT ON TABLE graph_checkpoints IS 'LangGraph state checkpoints';
COMMENT ON TABLE buyer_profiles IS 'Buyer profiles for plastic brokerage';
COMMENT ON TABLE supplier_profiles IS 'Supplier profiles for plastic brokerage';
COMMENT ON TABLE transactions IS 'Material transactions';
COMMENT ON TABLE material_edges IS 'Material relationship graph edges';
COMMENT ON TABLE entity_metadata IS 'Generic entity metadata store';
