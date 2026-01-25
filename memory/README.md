---
dora:
  version: "1.0"
  type: subsystem_readme
  generated: "2026-01-25 19:42:30 UTC"
  generator: scripts/generate_subsystem_readmes.py
  config: config/subsystems/readme_config.yaml
  time_verified: "system clock (UNVERIFIED - no API response)"
  auto_generated: true
---

# Memory Substrate

> **Tier:** CORE | **Path:** `memory` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                             Memory Substrate                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │      memory     │ ───► │  Outbound   │                  │
│  │ Dependencies│      │   Module    │      │ Dependencies│                  │
│  └─────────────┘      └─────────────┘      └─────────────┘                  │
│                              │                                              │
│                              ▼                                              │
│                    ┌─────────────────┐                                      │
│                    │  Memory/Audit   │                                      │
│                    │   Substrate     │                                      │
│                    └─────────────────┘                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Overview

Multi-layer memory with PacketEnvelope storage, semantic search, and audit trails

**Purpose:** Provides PacketEnvelope storage, semantic search, retrieval, deduplication, and audit trails.

**What depends on it:** `core/agents/executor.py`, `api/memory/router.py`, `mcp_memory/src/`

---

## Responsibilities and Boundaries

### What This Module Owns

- PacketEnvelope ingestion and storage
- Semantic search via embeddings
- Memory retrieval and ranking
- Deduplication enforcement
- Audit trail maintenance
- Graph memory synchronization

### What This Module Does NOT Do

- Agent execution (owned by core/agents)
- API routing (owned by api/)
- External client communication (owned by mcp_memory/)

### Inbound Dependencies

| Module | Purpose |
|--------|---------|
| `core/agents/executor.py` | Uses this module |
| `api/memory/router.py` | Uses this module |
| `mcp_memory/src/` | Uses this module |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| `runtime/redis_client.py` | Required dependency |
| `config/di_config.py` | Required dependency |

---

## Directory Layout

```
memory/
├── __init__.py
├── active_encoder.py
├── agent_persistence.py
├── audit_utils.py
├── blob_store.py
├── checkpoint/__init__.py
├── checkpoint/cursor_checkpoint_manager.py
├── checkpoint/postgres_saver.py
├── checkpoint_manager.py
├── checkpoint_metrics.py
├── checkpoint_validator.py
├── consolidation.py
├── context_builder.py
├── cross_encoder_reranker.py
├── cypher_templates.py
└── ... (65 more files)
```

| File | Purpose |
|------|---------|
| `substrate_service.py` | MemorySubstrateService - core ingestion, search, retrieval (PROTECTED) |
| `substrate_dag.py` | Ingestion DAG and processing pipeline (PROTECTED) |
| `substrate_models.py` | PacketEnvelope and data models (PROTECTED) |
| `retrieval.py` | Memory retrieval strategies and ranking |
| `semantic_search.py` | Vector-based semantic search implementation |
| `context_builder.py` | Context assembly for agent execution |
| `insight_extraction.py` | Pattern recognition and insight mining |
| `consolidation.py` | Memory consolidation and cleanup workflows |
| `deduplication.py` | Deduplication engine for packet uniqueness |
| `graph_memory.py` | Neo4j graph memory adapter |

### Naming Conventions

- **Packets:** `PacketEnvelope` with `kind`, `payload`, `metadata`
- **IDs:** UUIDv4 for all packet identifiers
- **Timestamps:** UTC ISO-8601 format
- **Embeddings:** `list[float]` with dimension 1536 or 3072

---

## Key Components

### `cross_encoder_reranker.py` — CrossEncoderConfig

```python
class CrossEncoderConfig:
    """Configuration for cross-encoder re-ranking."""
    
    # Key methods:

```

**Lines:** 74-93 in `cross_encoder_reranker.py`

### `cross_encoder_reranker.py` — RerankingResult

```python
class RerankingResult:
    """Result from cross-encoder re-ranking."""
    
    # Key methods:

```

**Lines:** 113-129 in `cross_encoder_reranker.py`

### `cross_encoder_reranker.py` — CrossEncoderReranker

```python
class CrossEncoderReranker:
    """Cross-encoder based neural re-ranker for improved retrieval quality."""
    
    # Key methods:

    async def __init__(self, ...): ...

    async def is_available(self, ...): ...

    async def _load_model(self, ...): ...

    async def rerank(self, ...): ...

    async def _extract_text(self, ...): ...

```

**Public Methods:** `__init__`, `is_available`, `_load_model`, `rerank`, `_extract_text`

**Lines:** 137-337 in `cross_encoder_reranker.py`

### `warming_models.py` — GapSeverity

```python
class GapSeverity:
    """Enumeration of knowledge gap severity levels."""
    
    # Key methods:

```

**Lines:** 51-57 in `warming_models.py`

### `warming_models.py` — KnowledgeGap

```python
class KnowledgeGap:
    """Represents a detected knowledge gap with metadata for prioritization."""
    
    # Key methods:

```

**Lines:** 61-72 in `warming_models.py`


---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`StrategyRetrievalRequest`** — Request parameters for strategy retrieval.
- **`SchemaSnapshot`** — Complete schema snapshot.
- **`SchemaIntrospector`** — Unified schema introspector for both PostgreSQL and Neo4j.

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MemoryRequest(BaseModel):
    """Request model for memory operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class MemoryResponse(BaseModel):
    """Response model for memory operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **All packet IDs are UUIDv4**
- **All timestamps are UTC ISO-8601**
- **PacketEnvelope is the canonical data structure for all memory writes**
- **Embeddings are list[float] with dimension 1536 or 3072**
- **Deduplication via dedup_key prevents duplicate ingestion**

---

## Execution and Lifecycle

### Startup

1. **Connection:** Establish PostgreSQL and Redis connections.
2. **Schema validation:** Verify database schema is current.
3. **Index loading:** Load vector indices for semantic search.
4. **Ready:** Service ready to accept ingestion and search requests.


### Main Execution

1. **Ingestion:** Receive PacketEnvelope → validate → check dedup → store.
2. **Embedding:** Generate embedding async if content present.
3. **Graph sync:** Sync to Neo4j if graph_memory enabled.
4. **Search:** Vector search → rank results → return with metadata.


### Shutdown

1. **Flush:** Complete pending writes.
2. **Disconnect:** Close database connections gracefully.
3. **Log:** Emit shutdown complete event.


### Background Tasks

Embedding generation, graph sync, and consolidation run as background tasks.

---

## Configuration

### Feature Flags

```yaml
# Memory feature flags
L9_ENABLE_MEMORY_TRACING: true  # Enable detailed tracing
L9_ENABLE_MEMORY_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_MEMORY_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
memory:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
MEMORY_LOG_LEVEL=INFO
MEMORY_TIMEOUT=30
MEMORY_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def get_cross_encoder_reranker()`

Get or create the CrossEncoderReranker singleton.

- **File:** `cross_encoder_reranker.py:348`
- **Async:** No

#### `def create_reranker_with_model(model_preset)`

Create a reranker with a specific model preset.

- **File:** `cross_encoder_reranker.py:356`
- **Async:** No

#### `def is_cross_encoder_available()`

Check if cross-encoder re-ranking is available.

- **File:** `cross_encoder_reranker.py:371`
- **Async:** No

#### `async def smoke_test()`

Run smoke test to verify memory system.

- **File:** `smoke_test.py:48`
- **Async:** Yes

#### `async def main()`

Main entrypoint for smoke test.

- **File:** `smoke_test.py:136`
- **Async:** Yes


### Usage Example

```python
from memory import MemorySubstrateService, PacketEnvelope
from datetime import datetime, timezone

service = MemorySubstrateService()

# Ingest a packet
packet = PacketEnvelope(
    source_id="cursor_session",
    agent_id="researcher-001",
    thread_id="thread-xyz",
    kind="REASONING",
    payload={"content": "Analysis of AI trends..."},
    metadata={"confidence": 0.85},
)
result = await service.ingest_packet(packet)

# Search memory
results = await service.search(
    query="AI trends analysis",
    limit=10,
    min_similarity=0.7,
)

for r in results:
    print(r.packet_id, r.similarity, r.payload)
```


---

## Observability

### Logging

Memory operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "memory",
  "message": "Operation completed",
  "correlation_id": "corr-xyz789",
  "agent_id": "agent-001",
  "duration_ms": 125
}
```

**Log Levels:**
- `DEBUG` — Detailed execution steps (off in production)
- `INFO` — Lifecycle events, successful operations
- `WARNING` — Timeouts, resource warnings, recoverable errors
- `ERROR` — Failures, exceptions, unrecoverable errors

### Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `memory_operation_duration_ms` | Histogram | Operation latency distribution |
| `memory_operation_total` | Counter | Total operations processed |
| `memory_error_total` | Counter | Total errors encountered |
| `memory_active_connections` | Gauge | Current active connections |

### Tracing

Memory emits OpenTelemetry spans:

- `memory.execute` — Root span for operation
  - `memory.validate` — Input validation
  - `memory.process` — Core processing
  - `memory.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/memory/`:
- `test_memory.py` — Core unit tests
- `test_memory_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test memory with real dependencies
- Test cross-subsystem interactions
- Test failure scenarios and recovery

### Known Edge Cases

1. **Duplicate packet** — Same dedup_key already exists → skip ingestion, return existing packet
1. **Embedding failure** — Embedding API unavailable → queue for retry, store without embedding
1. **Search timeout** — Vector search exceeds timeout → return partial results with warning
1. **Graph sync failure** — Neo4j unavailable → PostgreSQL is source of truth, retry graph sync
1. **Large payload** — Payload > 10KB → store in blob storage, reference in packet

---

## AI Usage Rules

### ✅ Allowed Scopes (AI can modify freely)

- `retrieval.py` — Application logic, safe to modify
- `semantic_search.py` — Application logic, safe to modify
- `context_builder.py` — Application logic, safe to modify
- `insight_extraction.py` — Application logic, safe to modify
- `consolidation.py` — Application logic, safe to modify
- `deduplication.py` — Application logic, safe to modify
- `graph_memory.py` — Application logic, safe to modify
- `tests/**` — Application logic, safe to modify
- `docs/**` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- `substrate_service.py` — Requires human review before merge
- `substrate_dag.py` — Requires human review before merge
- `substrate_models.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `substrate_service.py` — PROTECTED: Changes break system invariants
- `substrate_dag.py` — PROTECTED: Changes break system invariants
- `__init__.py` — PROTECTED: Changes break system invariants

### Required Pre-Reading

1. [`README-L9_ARCHITECTURE.md`](README-L9_ARCHITECTURE.md)
2. [`docs/CURSOR-RUNBOOK.md`](docs/CURSOR-RUNBOOK.md)
3. [`memory/README.md`](memory/README.md)

### Change Policy

All changes proposed by AI tools must:
1. Be scoped PRs with clear commit messages
2. Include tests (unit + integration where applicable)
3. Update documentation if APIs change
4. Respect feature flags for gradual rollout
5. Get human approval for restricted scopes
