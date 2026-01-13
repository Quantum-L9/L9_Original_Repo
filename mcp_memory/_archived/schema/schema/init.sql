-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schema
CREATE SCHEMA IF NOT EXISTS memory;

-- Short-term memory (< 1 hour)
CREATE TABLE IF NOT EXISTS memory.short_term (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT check_short_term_expires CHECK (expires_at > created_at)
);

-- Medium-term memory (< 24 hours)
CREATE TABLE IF NOT EXISTS memory.medium_term (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    importance FLOAT DEFAULT 1.0,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT check_medium_term_expires CHECK (expires_at > created_at)
);

-- Long-term memory (durable)
CREATE TABLE IF NOT EXISTS memory.long_term (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'user',
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    importance FLOAT DEFAULT 1.0,
    tags TEXT[] DEFAULT '{}',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    access_count INT DEFAULT 0,
    CONSTRAINT check_scope CHECK (scope IN ('user', 'project', 'global'))
);

-- HNSW Indexes (upgraded from IVFFlat)
CREATE INDEX idx_short_term_user_expires ON memory.short_term(user_id, expires_at);
CREATE INDEX idx_short_term_embedding ON memory.short_term USING hnsw(embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_medium_term_user_expires ON memory.medium_term(user_id, expires_at);
CREATE INDEX idx_medium_term_importance ON memory.medium_term(user_id, importance DESC) WHERE expires_at > CURRENT_TIMESTAMP;
CREATE INDEX idx_medium_term_embedding ON memory.medium_term USING hnsw(embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_long_term_user_scope ON memory.long_term(user_id, scope);
CREATE INDEX idx_long_term_kind ON memory.long_term(kind);
CREATE INDEX idx_long_term_tags ON memory.long_term USING GIN(tags);
CREATE INDEX idx_long_term_embedding ON memory.long_term USING hnsw(embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_long_term_access ON memory.long_term(last_accessed_at DESC);

-- Stats view
CREATE OR REPLACE VIEW memory.stats_view AS
SELECT 'short_term' as memory_type, COUNT(*) as total_count, COUNT(DISTINCT user_id) as unique_users, AVG(importance) as avg_importance, NOW() as calculated_at FROM memory.short_term WHERE expires_at > CURRENT_TIMESTAMP
UNION ALL SELECT 'medium_term', COUNT(*), COUNT(DISTINCT user_id), AVG(importance), NOW() FROM memory.medium_term WHERE expires_at > CURRENT_TIMESTAMP
UNION ALL SELECT 'long_term', COUNT(*), COUNT(DISTINCT user_id), AVG(importance), NOW() FROM memory.long_term;

-- Audit log
CREATE TABLE IF NOT EXISTS memory.audit_log (
    id BIGSERIAL PRIMARY KEY,
    operation TEXT NOT NULL,
    table_name TEXT,
    memory_id BIGINT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'success',
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user_timestamp ON memory.audit_log(user_id, created_at DESC);
