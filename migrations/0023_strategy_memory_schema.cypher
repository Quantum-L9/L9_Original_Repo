// =============================================================================
// Migration: 0023_strategy_memory_schema.cypher
// Strategy Memory for Repeat Task Optimization - Neo4j Schema
// =============================================================================
// Version: 1.0.0
// Created: 2026-01-20
// GMP: GMP-102 Strategy Memory Phase 0-1
// =============================================================================

// -----------------------------------------------------------------------------
// CONSTRAINTS (ensure uniqueness and data integrity)
// -----------------------------------------------------------------------------

// Strategy node - unique ID
CREATE CONSTRAINT strategy_id_unique IF NOT EXISTS
FOR (s:Strategy) REQUIRE s.id IS UNIQUE;

// Task node - unique ID
CREATE CONSTRAINT task_id_unique IF NOT EXISTS
FOR (t:Task) REQUIRE t.id IS UNIQUE;

// Execution node - unique ID
CREATE CONSTRAINT execution_id_unique IF NOT EXISTS
FOR (e:Execution) REQUIRE e.id IS UNIQUE;

// -----------------------------------------------------------------------------
// INDEXES (optimize query performance)
// -----------------------------------------------------------------------------

// Strategy indexes for retrieval
CREATE INDEX strategy_performance_idx IF NOT EXISTS
FOR (s:Strategy) ON (s.performance_score);

CREATE INDEX strategy_last_used_idx IF NOT EXISTS
FOR (s:Strategy) ON (s.last_used);

CREATE INDEX strategy_tags_idx IF NOT EXISTS
FOR (s:Strategy) ON (s.tags);

CREATE INDEX strategy_task_kind_idx IF NOT EXISTS
FOR (s:Strategy) ON (s.task_kind);

// Task indexes
CREATE INDEX task_strategy_idx IF NOT EXISTS
FOR (t:Task) ON (t.strategy_id);

CREATE INDEX task_order_idx IF NOT EXISTS
FOR (t:Task) ON (t.execution_order);

// Execution indexes
CREATE INDEX execution_strategy_idx IF NOT EXISTS
FOR (e:Execution) ON (e.strategy_id);

CREATE INDEX execution_timestamp_idx IF NOT EXISTS
FOR (e:Execution) ON (e.timestamp);

CREATE INDEX execution_success_idx IF NOT EXISTS
FOR (e:Execution) ON (e.success);

// -----------------------------------------------------------------------------
// VECTOR INDEX (for embedding similarity search)
// Note: Neo4j 5.11+ required for native vector index
// Falls back to brute-force if not available
// -----------------------------------------------------------------------------

// Uncomment if using Neo4j 5.11+ with vector index support:
// CREATE VECTOR INDEX strategy_embedding_idx IF NOT EXISTS
// FOR (s:Strategy) ON (s.context_embedding)
// OPTIONS {indexConfig: {
//   `vector.dimensions`: 1536,
//   `vector.similarity_function`: 'cosine'
// }};

// -----------------------------------------------------------------------------
// SAMPLE SCHEMA DOCUMENTATION
// -----------------------------------------------------------------------------

// Strategy Node Schema:
// {
//   id: String (UUID),
//   name: String,
//   description: String,
//   task_kind: String,
//   context_embedding: List<Float> (1536-dim),
//   graph_signature: String (SHA256 hash of plan structure),
//   plan_payload: String (JSON serialized ExecutionPlan),
//   performance_score: Float (0.0-1.0, exponential smoothing),
//   generality_score: Float (0.0-1.0, % tasks adapted),
//   confidence: Float (0.0-1.0, retrieval confidence),
//   usage_count: Integer,
//   success_count: Integer,
//   failure_count: Integer,
//   tags: List<String>,
//   created_at: DateTime,
//   last_used: DateTime,
//   schema_version: String
// }

// Task Node Schema:
// {
//   id: String (UUID),
//   strategy_id: String (FK to Strategy),
//   execution_order: Integer,
//   task_type: String (enum: agent_action, check, coordination),
//   agent_target: String,
//   name: String,
//   description: String,
//   parameters: String (JSON),
//   depends_on: List<String> (Task IDs)
// }

// Execution Node Schema:
// {
//   id: String (UUID),
//   strategy_id: String (FK to Strategy),
//   task_id: String (original task ID),
//   success: Boolean,
//   outcome_score: Float (0.0-1.0),
//   execution_time_ms: Integer,
//   resource_cost: Float,
//   failure_reason: String (nullable),
//   was_adapted: Boolean,
//   adaptation_distance: Integer (nullable),
//   timestamp: DateTime,
//   executor_id: String
// }

// -----------------------------------------------------------------------------
// RELATIONSHIP TYPES
// -----------------------------------------------------------------------------

// Strategy -[:DECOMPOSES_INTO]-> Task
// Strategy decomposition into sub-tasks (HTN structure)

// Task -[:DEPENDS_ON]-> Task
// Task dependency ordering

// Task -[:COORDINATES_WITH]-> Task
// Parallel task coordination

// Strategy -[:EXECUTED_AS]-> Execution
// Execution history tracking

// Strategy -[:DERIVED_FROM]-> Strategy
// Strategy lineage/adaptation history (Phase 2+)

// -----------------------------------------------------------------------------
// MIGRATION VERIFICATION QUERY
// -----------------------------------------------------------------------------

// Run this to verify migration applied:
// CALL db.constraints() YIELD name WHERE name STARTS WITH 'strategy_' OR name STARTS WITH 'task_' OR name STARTS WITH 'execution_' RETURN name;
// CALL db.indexes() YIELD name WHERE name STARTS WITH 'strategy_' OR name STARTS WITH 'task_' OR name STARTS WITH 'execution_' RETURN name;
