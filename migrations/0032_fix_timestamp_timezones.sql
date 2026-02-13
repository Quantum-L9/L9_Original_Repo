-- Migration: 0032_fix_timestamp_timezones.sql
-- Description: Alter naive timestamp columns to timestamp with time zone to ensure ADR-0083 compliance and resolve ingestion errors.
-- Created: 2026-02-13 05:30 EST

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
