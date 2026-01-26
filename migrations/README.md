# L9 Memory Substrate Migrations

## Overview

The L9 Memory Substrate is a multi-layered, multi-tenant memory system designed for autonomous AI agents. It provides:

- **Packet-based event logging** - Every agent action becomes a traceable packet
- **Semantic vector search** - pgvector-powered similarity search
- **Knowledge graph** - Entity relationships and fact extraction
- **Self-reflection** - Lessons learned, patterns, and failure analysis
- **Multi-tenancy** - Full tenant/org/user isolation via Row Level Security

---

## Migration Sequence

Apply migrations **in order**. Each builds on the previous.

| #      | File                                    | Purpose                       | Tables Created                 |
| ------ | --------------------------------------- | ----------------------------- | ------------------------------ |
| 1      | `0001_init_memory_substrate.sql`        | Core schema foundation        | 11 tables                      |
| 2      | `0002_enhance_packet_store.sql`         | Threading & lineage           | (extends packet_store)         |
| 3      | `0003_init_tasks.sql`                   | Task queue                    | tasks                          |
| 4      | `0004_init_world_model_entities.sql`    | World model entities          | world_model_entities           |
| 5      | `0005_init_knowledge_facts.sql`         | Knowledge graph facts         | knowledge_facts                |
| 6      | `0006_init_world_model_updates.sql`     | World model audit log         | world_model_updates            |
| 7      | `0007_init_world_model_snapshots.sql`   | World model snapshots         | world_model_snapshots          |
| 8      | `0008_memory_substrate_10x.sql`         | 10X upgrade + multi-tenant    | 6 new + extensions             |
| 9      | `0009_feedback_and_effectiveness.sql`   | Feedback loop + effectiveness | feedback_events + enhancements |
| 10     | `0011_tool_audit_log.sql`               | Tool execution audit          | tool_audit_log                 |
| 11     | `0012_fix_graph_checkpoints_unique.sql` | Fix unique constraint         | (fixes graph_checkpoints)      |
| 12     | `0013_mcp_audit_columns.sql`            | MCP audit governance          | (extends tool_audit_log)       |
| 13     | `0014_multi_checkpoint_support.sql`     | Multi-checkpoint support      | (extends graph_checkpoints)    |
| 14     | `0015_knowledge_facts_upsert_key.sql`   | Knowledge facts upsert        | (extends knowledge_facts)      |
| 15     | `0016_governance_scope_semantics.sql`   | Governance scope semantics    | governance_scopes              |
| 16     | `0017_governance_project_id.sql`        | Governance project ID         | (extends governance)           |
| 17     | `0018_semantic_facts.sql`               | Semantic facts                | semantic_facts                 |
| 18     | `0019_episodic_events.sql`              | Episodic events               | episodic_events                |
| 19     | `0020_optimize_vector_search.sql`       | Vector search optimization    | (indexes)                      |
| 20     | `0021_gmp_learning.sql`                 | GMP learning                  | gmp_learning                   |
| 21     | `0022_temporal_fact_validity.sql`       | Temporal fact validity        | (extends knowledge_facts)      |
| 22     | `0024_cmts_schema.sql`                  | CMTS schema                   | cmts\_\* tables                |
| **25** | **`0025_tool_embeddings.sql`**          | **GMP-78: Tool embeddings**   | **tool_embeddings**            |

---

## Migration Details

### 0001_init_memory_substrate.sql (Core Foundation)

**Version:** 1.0.0
**Extensions Required:** `uuid-ossp`, `vector`

Creates the core tables:

| Table                 | Purpose                                                 |
| --------------------- | ------------------------------------------------------- |
| `packet_store`        | Central event log for all PacketEnvelopes               |
| `semantic_memory`     | Vector embeddings (1536-dim) for semantic search        |
| `agent_memory_events` | Structured agent memory with packet references          |
| `reasoning_traces`    | Inference steps, confidence scores, decision tokens     |
| `agent_log`           | Centralized logging (DEBUG/INFO/WARNING/ERROR/CRITICAL) |
| `graph_checkpoints`   | LangGraph state persistence for recovery                |
| `buyer_profiles`      | Domain: buyer entities                                  |
| `supplier_profiles`   | Domain: supplier entities                               |
| `transactions`        | Domain: material transactions                           |
| `material_edges`      | Domain: material relationship graph                     |
| `entity_metadata`     | Generic extensible entity store                         |

**Key Indexes:**

- HNSW index on `semantic_memory.vector` for fast similarity search
- Timestamp DESC indexes on all tables for recency queries

---

### 0002_enhance_packet_store.sql (Threading & Lineage)

**Version:** 1.1.0
**Adds to:** `packet_store`

New columns:

| Column       | Type      | Purpose                                      |
| ------------ | --------- | -------------------------------------------- |
| `thread_id`  | UUID      | Link packets in conversation/session threads |
| `parent_ids` | UUID[]    | Multi-parent DAG lineage tracking            |
| `tags`       | TEXT[]    | Flexible labels for filtering                |
| `ttl`        | TIMESTAMP | Expiration for memory hygiene                |

**Key Indexes:**

- GIN index on `parent_ids` for lineage traversal
- GIN index on `tags` for tag filtering
- Partial index on `ttl` for expiration queries

---

### 0003_init_tasks.sql (Task Queue)

**Purpose:** OS-level task tracking and debugging

| Column         | Type      | Purpose                          |
| -------------- | --------- | -------------------------------- |
| `id`           | SERIAL    | Task ID                          |
| `type`         | TEXT      | Task type (default: 'generic')   |
| `status`       | TEXT      | pending/running/completed/failed |
| `payload`      | JSONB     | Task input                       |
| `result`       | JSONB     | Task output                      |
| `error`        | TEXT      | Error message if failed          |
| `created_at`   | TIMESTAMP | Creation time                    |
| `completed_at` | TIMESTAMP | Completion time                  |

---

### 0004_init_world_model_entities.sql (World Model Core)

**Purpose:** Persistent storage for world model entities

| Column        | Type  | Purpose                       |
| ------------- | ----- | ----------------------------- |
| `entity_id`   | TEXT  | Unique entity identifier (PK) |
| `entity_type` | TEXT  | Type classification           |
| `attributes`  | JSONB | Entity properties             |
| `confidence`  | FLOAT | Confidence score (0.0-1.0)    |
| `version`     | INT   | Optimistic locking version    |

**Key Indexes:**

- GIN index on `attributes` for JSONB queries
- Confidence index for filtering low-confidence entities

---

### 0005_init_knowledge_facts.sql (Knowledge Graph)

**Purpose:** Subject-Predicate-Object triples for knowledge representation

| Column          | Type  | Purpose                     |
| --------------- | ----- | --------------------------- |
| `fact_id`       | UUID  | Unique fact ID              |
| `subject`       | TEXT  | Entity being described      |
| `predicate`     | TEXT  | Relationship/attribute type |
| `object`        | JSONB | Value or related entity     |
| `confidence`    | FLOAT | Extraction confidence       |
| `source_packet` | UUID  | Link to originating packet  |

**Key Indexes:**

- Composite index on `(subject, predicate)` for graph queries
- GIN index on `object` for JSONB search

---

### 0006_init_world_model_updates.sql (Audit Log)

**Purpose:** Track all updates applied to the world model

| Column                 | Type  | Purpose               |
| ---------------------- | ----- | --------------------- |
| `update_id`            | UUID  | Unique update ID      |
| `insight_id`           | UUID  | Source insight        |
| `insight_type`         | TEXT  | Type of insight       |
| `entities`             | JSONB | Affected entity IDs   |
| `content`              | JSONB | Update payload        |
| `state_version_before` | INT   | Version before update |
| `state_version_after`  | INT   | Version after update  |

---

### 0007_init_world_model_snapshots.sql (Point-in-Time State)

**Purpose:** Full world model state snapshots for recovery

| Column           | Type  | Purpose                  |
| ---------------- | ----- | ------------------------ |
| `snapshot_id`    | UUID  | Unique snapshot ID       |
| `snapshot`       | JSONB | Full state serialization |
| `state_version`  | INT   | Version at snapshot time |
| `entity_count`   | INT   | Number of entities       |
| `relation_count` | INT   | Number of relations      |
| `description`    | TEXT  | Reason for snapshot      |

---

### 0008_memory_substrate_10x.sql (10X Upgrade + Multi-Tenant)

**Version:** 2.1.0
**Extensions Required:** `uuid-ossp`, `vector`, `pgcrypto`
**Dependencies:** 0001-0007 must be applied first

This is the major upgrade migration that adds:

#### New Tables (6)

| Table                  | Purpose                                                        |
| ---------------------- | -------------------------------------------------------------- |
| `memory_embeddings`    | Multi-space vectors (content/context/entity/summary/reasoning) |
| `memory_access_log`    | Usage tracking for importance learning                         |
| `entity_relationships` | Knowledge graph edges for traversal                            |
| `memory_summaries`     | Consolidated long-term memories                                |
| `reflection_store`     | Persistent lessons, patterns, failures                         |
| `task_reflections`     | Per-task outcome-based learning                                |

#### Multi-Tenant Identity (4 Core Fields)

Added to ALL memory tables:

| Field            | Type | Purpose                     |
| ---------------- | ---- | --------------------------- |
| `tenant_id`      | UUID | Top-level tenant isolation  |
| `org_id`         | UUID | Organization within tenant  |
| `user_id`        | UUID | User within organization    |
| `correlation_id` | UUID | Request/session correlation |

Plus tracing: `session_id`, `trace_id`

#### Enhanced Existing Tables

**packet_store additions:**

- `scope` - Memory isolation (shared/cursor/l-private)
- `importance_score` - Learned importance (0.0-1.0)
- `access_count` - Retrieval counter
- `last_accessed` - Last access timestamp
- `contradiction_count` - Times contradicted
- `content_hash` - Deduplication hash
- `chunk_count`, `is_chunked` - Chunking metadata

**knowledge_facts additions:**

- `subject_normalized`, `object_normalized` - Entity normalization
- `supporting_packet_count` - Evidence count
- `access_count`, `last_accessed` - Usage tracking

**semantic_memory additions:**

- `importance_score`, `access_count` - Importance tracking
- `embedding_type` - Vector type classification
- `scope` - Memory isolation

#### Helper Functions

| Function                                | Purpose                       |
| --------------------------------------- | ----------------------------- |
| `l9_set_scope(tenant, org, user, role)` | Set session scope for RLS     |
| `l9_current_tenant()`                   | Get current tenant UUID       |
| `l9_current_org()`                      | Get current org UUID          |
| `l9_current_user_id()`                  | Get current user UUID         |
| `l9_current_role()`                     | Get current role              |
| `l9_is_admin()`                         | Check if admin                |
| `update_packet_access(packet_id)`       | Track packet access           |
| `decay_fact_confidence(fact_id)`        | Decay on contradiction        |
| `reinforce_fact_confidence(fact_id)`    | Reinforce on support          |
| `temporal_weight(timestamp)`            | Calculate decay weight        |
| `combined_importance(...)`              | Calculate ranking score       |
| `normalize_entity(name)`                | Normalize entity names        |
| `upsert_entity_relationship(...)`       | Insert/reinforce relationship |

#### Materialized Views

| View                        | Purpose                                   | Refresh |
| --------------------------- | ----------------------------------------- | ------- |
| `mv_agent_recent_important` | Recent high-importance memories per agent | Daily   |
| `mv_entity_graph`           | Aggregated entity relationships           | Daily   |
| `mv_high_confidence_facts`  | Top facts by combined score               | Daily   |
| `mv_reflection_patterns`    | Reflection statistics by type             | Daily   |

#### Row Level Security

4 policies per table:

1. **Tenant Isolation** - Filter by `app.tenant_id`
2. **Org Isolation** - Filter by `app.org_id`
3. **Admin Override** - Bypass for platform_admin/tenant_admin
4. **User Visibility** - End users see only their rows

---

## How to Apply Migrations

### Fresh Install

```bash
cd /opt/l9
psql -U l9_user -d l9 -f migrations/0001_init_memory_substrate.sql
psql -U l9_user -d l9 -f migrations/0002_enhance_packet_store.sql
psql -U l9_user -d l9 -f migrations/0003_init_tasks.sql
psql -U l9_user -d l9 -f migrations/0004_init_world_model_entities.sql
psql -U l9_user -d l9 -f migrations/0005_init_knowledge_facts.sql
psql -U l9_user -d l9 -f migrations/0006_init_world_model_updates.sql
psql -U l9_user -d l9 -f migrations/0007_init_world_model_snapshots.sql
psql -U l9_user -d l9 -f migrations/0008_memory_substrate_10x.sql
psql -U l9_user -d l9 -f migrations/0009_feedback_and_effectiveness.sql
psql -U l9_user -d l9 -f migrations/0011_tool_audit_log.sql
psql -U l9_user -d l9 -f migrations/0012_fix_graph_checkpoints_unique.sql
psql -U l9_user -d l9 -f migrations/0013_mcp_audit_columns.sql
```

### Upgrade from Existing

If you already have 0001-0007, run:

```bash
psql -U l9_user -d l9 -f migrations/0008_memory_substrate_10x.sql
psql -U l9_user -d l9 -f migrations/0009_feedback_and_effectiveness.sql
psql -U l9_user -d l9 -f migrations/0011_tool_audit_log.sql
psql -U l9_user -d l9 -f migrations/0012_fix_graph_checkpoints_unique.sql
psql -U l9_user -d l9 -f migrations/0013_mcp_audit_columns.sql
```

---

## Multi-Tenant Usage

### Set Session Scope

Before any query, set the session context:

```sql
SELECT l9_set_scope(
    'tenant-uuid'::uuid,
    'org-uuid'::uuid,
    'user-uuid'::uuid,
    'end_user'  -- or 'org_admin', 'tenant_admin', 'platform_admin'
);
```

### Check Current Context

```sql
SELECT
    l9_current_tenant() as tenant,
    l9_current_org() as org,
    l9_current_user_id() as user_id,
    l9_current_role() as role;
```

### Admin Access (Bypass RLS)

```sql
SELECT l9_set_scope(tenant_uuid, org_uuid, user_uuid, 'platform_admin');
-- Now queries see all data
```

### Backfill Existing Data

```sql
UPDATE packet_store SET
    tenant_id = 'default-tenant-uuid'::uuid,
    org_id = 'default-org-uuid'::uuid,
    user_id = 'default-user-uuid'::uuid
WHERE tenant_id IS NULL;

-- Repeat for other tables...
```

---

## Memory Scopes

The `scope` column provides additional filtering:

| Scope       | Who Can See                 |
| ----------- | --------------------------- |
| `shared`    | Everyone                    |
| `cursor`    | Cursor sessions + admins    |
| `l-private` | L9 system + platform admins |

---

## Maintenance Jobs

Run via pg_cron or external scheduler:

```sql
-- Daily: Refresh materialized views
CALL refresh_memory_views();

-- Daily: Decay unaccessed packet importance
CALL decay_unaccessed_importance(30, 0.1);

-- Daily: Evict expired TTL packets
CALL evict_expired_packets();

-- Daily: Evict expired reflections
CALL evict_expired_reflections();
```

---

## Table Counts

After all migrations:

| Category     | Tables                                                                                                 |
| ------------ | ------------------------------------------------------------------------------------------------------ |
| Core Memory  | 6 (packet_store, semantic_memory, agent_memory_events, reasoning_traces, agent_log, graph_checkpoints) |
| Domain       | 4 (buyer_profiles, supplier_profiles, transactions, material_edges, entity_metadata)                   |
| World Model  | 3 (world_model_entities, world_model_updates, world_model_snapshots)                                   |
| Knowledge    | 2 (knowledge_facts, entity_relationships)                                                              |
| Reflection   | 2 (reflection_store, task_reflections)                                                                 |
| Intelligence | 2 (memory_embeddings, memory_summaries)                                                                |
| Operations   | 3 (tasks, memory_access_log, tool_audit_log)                                                           |
| Feedback     | 1 (feedback_events)                                                                                    |
| **Total**    | **22 tables**                                                                                          |

---

### 0009_feedback_and_effectiveness.sql (Feedback Loop)

**Version:** 1.0.0
**Dependencies:** 0008_memory_substrate_10x.sql must be applied first

Adds Emma's feedback loop patterns:

| Table/Enhancement               | Purpose                                                                                   |
| ------------------------------- | ----------------------------------------------------------------------------------------- |
| `feedback_events`               | Structured feedback from users on agent outputs                                           |
| `reflection_store` enhancements | Effectiveness tracking (success_count, failure_count, effectiveness_score, times_applied) |

**Key Features:**

- Feedback types: positive, negative, correction, preference, question, clarification
- Sentiment scoring (-1.0 to 1.0)
- Links to packets, reflections, tasks
- Processing status and derived reflections
- Multi-tenant support

---

### 0011_tool_audit_log.sql (Tool Execution Audit)

**Version:** 1.0.0
**Dependencies:** None (standalone table)

Tracks all tool executions with cost and performance metrics:

| Column        | Type         | Purpose                  |
| ------------- | ------------ | ------------------------ |
| `id`          | BIGSERIAL    | Primary key              |
| `tool_name`   | VARCHAR(255) | Tool identifier          |
| `agent_id`    | VARCHAR(255) | Agent that executed tool |
| `input_data`  | JSONB        | Tool input               |
| `output_data` | JSONB        | Tool output              |
| `duration_ms` | FLOAT        | Execution time           |
| `tokens_used` | INT          | Token consumption        |
| `cost_usd`    | FLOAT        | Cost in USD              |
| `error`       | TEXT         | Error message if failed  |
| `timestamp`   | TIMESTAMPTZ  | Execution time           |
| `request_id`  | UUID         | Request correlation      |

**Key Indexes:**

- Agent + timestamp for agent activity queries
- Tool + timestamp for tool usage analytics
- Request ID for request tracing

---

### 0012_fix_graph_checkpoints_unique.sql (Schema Fix)

**Version:** 1.0.0
**Dependencies:** 0001_init_memory_substrate.sql

Fixes missing UNIQUE constraint on `graph_checkpoints.agent_id` required for checkpoint upsert operations.

**Idempotent:** Safe to run multiple times.

---

### 0013_mcp_audit_columns.sql (MCP Governance Audit)

**Version:** 1.0.0
**Dependencies:** 0011_tool_audit_log.sql must be applied first

Adds governance columns to `tool_audit_log` for MCP memory server audit:

| Column       | Type | Purpose                                                     |
| ------------ | ---- | ----------------------------------------------------------- |
| `caller`     | TEXT | Caller identity: "L" (L-CTO kernel) or "C" (Cursor IDE)     |
| `project_id` | TEXT | Project identifier: "l9" for L9 repo, NULL for global scope |

**Key Indexes:**

- Caller + timestamp for governance queries
- Project + timestamp for multi-project isolation
- Composite (caller, project_id, timestamp) for governance audit

**Usage:**

- MCP server logs all tool calls to `tool_audit_log` with caller/project_id
- Replaces deprecated `memory.audit_log` from old MCP schema
- Enables governance tracking and multi-project isolation

---

### 0025_tool_embeddings.sql (GMP-78: Dynamic Tool Discovery)

**Version:** 1.0.0
**Dependencies:** pgvector extension (from 0001)
**GMP:** GMP-78 Phase 1

Creates the `tool_embeddings` table for semantic tool retrieval:

| Column                 | Type         | Purpose                                       |
| ---------------------- | ------------ | --------------------------------------------- |
| `tool_name`            | VARCHAR(255) | Primary key - unique tool identifier          |
| `description`          | TEXT         | Tool description (embedded for search)        |
| `category`             | VARCHAR(64)  | Tool category for filtering                   |
| `embedding`            | vector(1536) | OpenAI text-embedding-3-small vector          |
| `negative_constraints` | TEXT[]       | Array of "don't use when X" guidance          |
| `metadata`             | JSONB        | Additional metadata (risk_level, scope, etc.) |
| `created_at`           | TIMESTAMPTZ  | Creation timestamp                            |
| `updated_at`           | TIMESTAMPTZ  | Auto-updated on modification                  |

**Key Indexes:**

- ivfflat index on `embedding` for cosine similarity search
- B-tree index on `category` for filtering

**Key Features:**

- Enables semantic tool discovery instead of static tool binding
- Auto-synced at startup via `sync_all_tool_embeddings()`
- 40-70% token reduction vs loading all tools
- See ADR-0064 for full architecture

**Usage:**

```python
from core.tools import discover_tools_for_task

# At runtime (per task):
tools = await discover_tools_for_task("search memory for user")
# Returns: [{"type": "function", "function": {...}}]
```

---

_Last updated: 2026-01-25_
