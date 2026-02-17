---
dora:
  version: "1.0"
  type: subsystem_readme
  generated: "2026-02-17 00:14:44 UTC"
  generator: scripts/generate_subsystem_readmes.py
  config: config/subsystems/readme_config.yaml
  time_verified: "system clock (verification skipped)"
  auto_generated: true
---

# MCP Memory Server

> **Tier:** API | **Path:** `mcp_memory` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                            MCP Memory Server                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │    mcp_memory   │ ───► │  Outbound   │                  │
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

Model Context Protocol server for memory operations

**Purpose:** Provides MCP-compliant interface for memory read/write operations from external clients.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute mcp memory tasks
- **State management:** Maintain internal state with proper lifecycle
- **Logging:** Emit structured logs for all operations
- **Metrics:** Expose Prometheus-compatible metrics

### What This Module Does NOT Do

- **Authentication** — Handled by `api/auth.py`
- **External communication** — Handled by clients/adapters
- **Scheduling** — Handled by runtime/task_queue.py

### Inbound Dependencies

| Module | Purpose |
|--------|---------|
| — | No inbound dependencies |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| `memory/substrate_service.py` | Required dependency |

---

## Directory Layout

```
mcp_memory/
├── src/__init__.py
├── src/audit.py
├── src/config.py
├── src/control_plane/__init__.py
├── src/control_plane/config.py
├── src/db.py
├── src/embeddings.py
├── src/kernel/__init__.py
├── src/kernel/protocol.py
├── src/main.py
├── src/mcp_server.py
├── src/memory_substrate/__init__.py
├── src/memory_substrate/service.py
├── src/models.py
├── src/observability/__init__.py
└── ... (20 more files)
```

| File | Purpose |
|------|---------|
| `src/server.py` | Core module (PROTECTED) |
| `__init__.py` | Core module (PROTECTED) |
| `test_all_layers.py` | Tests for Redis connection and operations. |
| `test_all_layers.py` | Tests for PostgreSQL connection and operations. |
| `test_all_layers.py` | Tests for Neo4j connection and operations. |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `McpMemoryService`)
- **Functions:** `snake_case` (e.g., `process_mcp_memory_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `test_all_layers.py` — TestRedisLayer

```python
class TestRedisLayer:
    """Tests for Redis connection and operations."""

    # Key methods:

    async def redis_client(self, ...): ...

    async def test_redis_connection(self, ...): ...

    async def test_redis_set_get(self, ...): ...

    async def test_redis_rate_limiting(self, ...): ...

    async def test_redis_task_queue(self, ...): ...

```

**Public Methods:** `redis_client`, `test_redis_connection`, `test_redis_set_get`, `test_redis_rate_limiting`, `test_redis_task_queue`

**Lines:** 66-151 in `test_all_layers.py`

### `test_all_layers.py` — TestPostgresLayer

```python
class TestPostgresLayer:
    """Tests for PostgreSQL connection and operations."""

    # Key methods:

    async def pg_pool(self, ...): ...

    async def test_postgres_connection(self, ...): ...

    async def test_postgres_version(self, ...): ...

    async def test_pgvector_extension(self, ...): ...

    async def test_postgres_packet_store_table(self, ...): ...

```

**Public Methods:** `pg_pool`, `test_postgres_connection`, `test_postgres_version`, `test_pgvector_extension`, `test_postgres_packet_store_table`

**Lines:** 159-282 in `test_all_layers.py`

### `test_all_layers.py` — TestNeo4jLayer

```python
class TestNeo4jLayer:
    """Tests for Neo4j connection and operations."""

    # Key methods:

    async def neo4j_client(self, ...): ...

    async def test_neo4j_connection(self, ...): ...

    async def test_neo4j_simple_query(self, ...): ...

    async def test_neo4j_create_and_query_node(self, ...): ...

    async def test_neo4j_relationship(self, ...): ...

```

**Public Methods:** `neo4j_client`, `test_neo4j_connection`, `test_neo4j_simple_query`, `test_neo4j_create_and_query_node`, `test_neo4j_relationship`

**Lines:** 290-391 in `test_all_layers.py`

### `test_all_layers.py` — TestAllLayersIntegration

```python
class TestAllLayersIntegration:
    """Integration tests that span multiple layers."""

    # Key methods:

    async def test_all_layers_available(self, ...): ...

```

**Public Methods:** `test_all_layers_available`

**Lines:** 399-455 in `test_all_layers.py`

### `verify_main_pipeline_e2e.py` — Config

```python
class Config:
    """Configuration from environment."""

    # Key methods:

```

**Lines:** 59-78 in `verify_main_pipeline_e2e.py`


---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`TestRateLimitHTTPResponses`** — Test HTTP response behavior when rate limited.
- **`SaveMemoryRequest`** — Request model for saving a memory entry to the memory substrate.
- **`MemoryResponse`** — Response model representing a stored memory entry.

### Exported Symbols (`__all__`)

`AbstractMemoryRepository`, `AuditLogger`, `FeatureFlagService`, `MemoryRecord`, `Orchestrator`, `OrchestratorConfig`, `PACKET_TYPES`, `PacketEnvelope`, `PacketEnvelopeV2`, `PacketMetadata`

*...and 26 more*

### Module Constants

| Constant | Value | Line |
|----------|-------|------|
| `POSTGRES_DSN` | `os.getenv('MEMORY_DSN', os.getenv('DATAB...` | 46 |
| `REDIS_HOST` | `os.getenv('REDIS_HOST', '127.0.0.1')` | 52 |
| `REDIS_PORT` | `int(os.getenv('REDIS_PORT', '6379'))` | 53 |
| `NEO4J_URI` | `os.getenv('NEO4J_URL', os.getenv('NEO4J_...` | 56 |
| `NEO4J_USER` | `os.getenv('NEO4J_USER', 'neo4j')` | 57 |
| `NEO4J_PASSWORD` | `os.getenv('NEO4J_PASSWORD', '')` | 58 |
| `MAX_RETRIES` | `3` | 45 |
| `BASE_BACKOFF` | `0.5` | 46 |

*...and 6 more constants*

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class McpMemoryRequest(BaseModel):
    """Request model for mcp_memory operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class McpMemoryResponse(BaseModel):
    """Response model for mcp_memory operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **MCP protocol compliance**
- **All operations logged**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Mcp_Memory components are discovered and registered.
2. **Configuration:** Settings loaded from environment and config files.
3. **Dependencies:** Required services (Redis, PostgreSQL, etc.) are connected.
4. **Initialization:** Internal state is initialized; ready for requests.

### Main Execution

1. **Request received:** Validate input against schema.
2. **Processing:** Execute core logic with appropriate error handling.
3. **State updates:** Persist any state changes atomically.
4. **Response:** Return structured response with timing metadata.

### Shutdown

1. **Graceful stop:** Stop accepting new requests.
2. **Drain:** Complete in-flight operations (with timeout).
3. **Cleanup:** Release resources, close connections.
4. **Log:** Emit shutdown complete event.

### Background Tasks

No background tasks. Operations are request-driven.

---

## Configuration

### Feature Flags

```yaml
# Mcp_Memory feature flags
L9_ENABLE_MCP_MEMORY_TRACING: true  # Enable detailed tracing
L9_ENABLE_MCP_MEMORY_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_MCP_MEMORY_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
mcp_memory:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
MCP_MEMORY_LOG_LEVEL=INFO
MCP_MEMORY_TIMEOUT=30
MCP_MEMORY_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `async def test_save_memory_uses_main_pipeline_when_service_available()`

Test that save_memory_handler uses main pipeline when substrate_service is provided.

- **File:** `test_main_pipeline_integration.py:28`
- **Async:** Yes

#### `async def test_save_memory_falls_back_to_direct_db_when_service_unavailable()`

Test that save_memory_handler falls back to direct DB when substrate_service is None.

- **File:** `test_main_pipeline_integration.py:81`
- **Async:** Yes

#### `async def test_save_via_main_pipeline_creates_correct_packet_envelope()`

Test that _save_via_main_pipeline creates PacketEnvelopeIn with correct structure.

- **File:** `test_main_pipeline_integration.py:133`
- **Async:** Yes

#### `async def test_save_via_main_pipeline_handles_ttl_correctly()`

Test that _save_via_main_pipeline calculates TTL based on duration.

- **File:** `test_main_pipeline_integration.py:192`
- **Async:** Yes

#### `async def test_save_via_main_pipeline_handles_errors_gracefully()`

Test that _save_via_main_pipeline raises HTTPException on write failure.

- **File:** `test_main_pipeline_integration.py:234`
- **Async:** Yes


### Usage Example

```python
from mcp_memory import McpMemoryService

# Initialize
service = McpMemoryService()

# Execute operation
result = await service.execute(
    request_id="req-001",
    data={"key": "value"},
    correlation_id="corr-xyz789",
)

print(result.success)  # True
print(result.duration_ms)  # 125.5
```

---

## Observability

### Logging

Mcp Memory operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-17T00:14:44Z",
  "level": "INFO",
  "module": "mcp_memory",
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
| `mcp_memory_operation_duration_ms` | Histogram | Operation latency distribution |
| `mcp_memory_operation_total` | Counter | Total operations processed |
| `mcp_memory_error_total` | Counter | Total errors encountered |
| `mcp_memory_active_connections` | Gauge | Current active connections |

### Tracing

Mcp Memory emits OpenTelemetry spans:

- `mcp_memory.execute` — Root span for operation
  - `mcp_memory.validate` — Input validation
  - `mcp_memory.process` — Core processing
  - `mcp_memory.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/mcp_memory/`:
- `test_mcp_memory.py` — Core unit tests
- `test_mcp_memory_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test mcp_memory with real dependencies
- Test cross-subsystem interactions
- Test failure scenarios and recovery

### Known Edge Cases

1. **Timeout:** Operation exceeds deadline → Return partial result with timeout status.
2. **Invalid input:** Schema validation fails → Return 400 with validation errors.
3. **Dependency unavailable:** Required service down → Retry with exponential backoff, then fail gracefully.
4. **Resource exhaustion:** Memory/connections exceeded → Reject new requests, log alert.

---

## AI Usage Rules

### ✅ Allowed Scopes (AI can modify freely)

- `src/handlers/**` — Application logic, safe to modify
- `src/tools/**` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- `src/server.py` — Requires human review before merge
- `__init__.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `src/server.py` — PROTECTED: Changes break system invariants
- `__init__.py` — PROTECTED: Changes break system invariants

### Required Pre-Reading

1. [`README-L9_ARCHITECTURE.md`](README-L9_ARCHITECTURE.md)
2. [`docs/CURSOR-RUNBOOK.md`](docs/CURSOR-RUNBOOK.md)

### Change Policy

All changes proposed by AI tools must:
1. Be scoped PRs with clear commit messages
2. Include tests (unit + integration where applicable)
3. Update documentation if APIs change
4. Respect feature flags for gradual rollout
5. Get human approval for restricted scopes
