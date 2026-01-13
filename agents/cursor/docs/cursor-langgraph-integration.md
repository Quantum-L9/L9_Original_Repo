# Cursor + LangGraph + L9 Memory Integration

**Version:** 1.0.0  
**Date:** 2026-01-11  
**GMP ID:** GMP-48

## Overview

This document describes the architecture, flows, and operations for the Cursor + LangGraph + L9 Memory integration. This integration enables Cursor IDE to execute tasks through LangGraph with full memory substrate access, governance gates, and checkpointing.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Cursor IDE                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CursorExecutor                                │
│  - run_task()                                                    │
│  - resume_thread()                                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Application                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ PlanningNode │→ │ MemorySearch │→ │ DecisionGate  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │ MemoryWrite  │→ │ ErrorRecovery│                            │
│  └──────────────┘  └──────────────┘                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              CursorMemoryGateway                                  │
│  - write_decision()                                             │
│  - write_error()                                                │
│  - search_memory()                                              │
│  - Scope enforcement: developer, global only                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│          SubstrateDagOrchestrator                                │
│  - ingest_packet()                                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              L9 Memory Substrate                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ PacketStore  │  │ SemanticMem   │  │ WorldModel   │         │
│  │ (PostgreSQL) │  │ (pgvector)    │  │ (Neo4j)      │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Governance Loop (Igor)                              │
│  - ApprovalManager                                               │
│  - ApprovalGate (is_high_impact_decision)                       │
└─────────────────────────────────────────────────────────────────┘
```

## Flow Descriptions

### Decision Write Path

1. **CursorAgentState** accumulates decisions during LangGraph execution
2. **CursorMemoryWriteNode** calls `CursorMemoryGateway.write_decision()`
3. Gateway builds `PacketEnvelopeIn` with `packet_type="cursor_decision"`
4. Gateway calls `SubstrateDagOrchestrator.ingest_packet()`
5. DAG orchestrator routes through full pipeline:
   - `intake_node` → `reasoning_node` → `memory_write_node` → `semantic_embed_node` → `checkpoint_node`
6. Packet persisted to `packet_store` (PostgreSQL) as PacketEnvelope v2.0.0
7. Embedding generated and stored in `semantic_memory` (pgvector)

### Semantic Search Path

1. **CursorMemorySearchNode** calls `CursorMemoryGateway.search_memory()`
2. Gateway validates scope (must be `developer` or `global`)
3. Gateway calls `semantic_search()` wrapper
4. Wrapper builds `SemanticSearchRequest` and calls `MemorySubstrateService.semantic_search()`
5. Service queries pgvector for similar embeddings
6. Results mapped to `SearchHit` objects and returned
7. Hits written to state `search_hits` field

### Graph Search with Redis Cache

1. **GraphSearchContext** created with project_id, agent_id, freshness_level
2. `cached_graph_search()` computes query hash
3. Check Redis cache with key: `graph_search:{project_id}:{agent_id}:{query_hash}`
4. If cache hit and schema version matches: return cached results
5. If cache miss or schema mismatch:
   - Execute Neo4j query via `Neo4jClient`
   - Compute TTL (governance: 60-120s, exploratory: 300-600s) with ±10% jitter
   - Store results in Redis with schema version
6. Return `GraphSearchResult` with results and metadata

### Dual Checkpoint Path

1. **CursorCheckpointManager.checkpoint()** called after each node or phase
2. **Primary:** Save to PostgresSaver (LangGraph-native)
   - Maps `thread_id` to `agent_id` format: `"cursor:{thread_id}"`
   - Stores in `graph_checkpoints` table
3. **Fallback:** Save to PacketEnvelope (L9 substrate)
   - Creates `packet_type="cursor_checkpoint"` envelope
   - Stores full state in payload
   - Ingested via DAG orchestrator
4. **Restore:** `CursorCheckpointManager.restore()`
   - First tries PostgresSaver
   - Falls back to PacketEnvelope if PostgresSaver missing
   - Returns `CursorAgentState` for resume

### Igor Approval Path

1. **CursorDecisionGateNode** checks `is_high_impact_decision()`
2. Heuristics:
   - Decision type (git_commit, file_mutation, etc.)
   - Tool name (if requires approval per `Capability`)
   - File impact (memory substrate, governance, executor)
   - Tags (high_risk, production, secrets)
   - Confidence (< 0.7)
3. If high-impact:
   - Call `escalate_to_igor()` → `ApprovalManager.request_approval()`
   - Store `approval_id` in state
   - Block graph execution (pause at decision gate)
4. Igor approves/rejects via `ApprovalManager.approve()` / `reject()`
5. `handle_governance_result()` updates state:
   - Approved: Mark decision approved, continue execution
   - Rejected: Mark rejected, add guidance to reasoning_trace

## Operational Guidance

### Deployment

**Required Environment Variables:**

```bash
# PostgreSQL (for checkpoint saver)
DATABASE_URL=postgresql://user:pass@host:port/l9_memory

# Redis (for graph cache)
REDIS_URL=redis://localhost:6379/0

# Neo4j (for graph queries)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Igor approval threshold (optional)
IGOR_APPROVAL_THRESHOLD=0.7

# Graph cache TTLs (optional)
GRAPH_CACHE_TTL_GOVERNANCE_SEC=90
GRAPH_CACHE_TTL_DEFAULT_SEC=450
```

**Configuration:**

Load via `CursorLangGraphConfig`:

```python
from config.cursor_langgraph_config import get_cursor_langgraph_config

config = get_cursor_langgraph_config()
```

### Monitoring

**Logs to Watch:**

- `CursorExecutor`: Task start/complete, thread resume
- `CursorMemoryGateway`: Decision/error writes, scope violations
- `CursorCheckpointManager`: Checkpoint save/restore, dual checkpoint status
- `ApprovalGate`: High-impact decisions, escalation results
- `GraphSearchCache`: Cache hits/misses, schema version mismatches

**Observability Spans:**

- `cursor.task.execute` - Full task execution
- `cursor.memory.write` - Memory write operations
- `cursor.memory.search` - Semantic/graph search
- `cursor.checkpoint.save` - Checkpoint operations
- `cursor.governance.escalate` - Igor approval requests

### Failure Modes and Recovery

**Redis Unavailable:**
- Graph search falls back to direct Neo4j queries (no caching)
- No impact on checkpoint or memory writes
- Log warning, continue execution

**Neo4j Unavailable:**
- Graph search returns empty results
- No impact on semantic search or checkpoint
- Log error, continue execution

**PostgreSQL Unavailable:**
- PostgresSaver checkpoint fails (falls back to PacketEnvelope)
- Memory writes fail (circuit breaker opens after 5 failures)
- Log error, return error result

**Igor Unavailable:**
- Approval requests remain PENDING
- Graph execution blocks at decision gate
- Timeout after expiration (default: 1 hour)
- Log warning, mark as expired

**Checkpoint Recovery:**

1. Identify thread_id from interrupted task
2. Call `CursorExecutor.resume_thread(thread_id)`
3. Executor restores state from checkpoint (PostgresSaver or PacketEnvelope)
4. LangGraph resumes from last checkpoint
5. Task completes from restored state

## Schema Versions

- **PacketEnvelope:** v2.0.0 (canonical, immutable)
- **Graph Cache Schema:** Computed from `graph_search_query_builder.py` + world model schema hash
- **Checkpoint Schema:** LangGraph-native (PostgresSaver) + PacketEnvelope v2.0.0 (fallback)

## Scope Enforcement

Cursor can only access:
- `"developer"` - Developer-scoped memories
- `"global"` - Global/shared memories

Cursor **cannot** access:
- `"l-private"` - L-CTO private memories
- Any other scopes

Violations raise `CursorScopeViolationError` and are logged for governance.

## Testing

Run integration tests:

```bash
pytest tests/integration/test_cursor_langgraph_integration.py -v
```

Tests cover:
1. Decision write to packetstore v2.0.0
2. Semantic search hits pgvector
3. Graph search uses Redis cache
4. Igor high-impact decision escalation
5. Checkpoint and resume thread
6. Scope enforcement (Cursor cannot read l-private)

## Related Documentation

- [Memory Substrate README](../memory/README.md)
- [Governance Approval Manager](../../core/governance/approval_manager.py)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)

