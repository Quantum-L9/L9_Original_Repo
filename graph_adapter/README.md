---
dora:
  version: "1.0"
  type: subsystem_readme
  generated: "2026-02-14 08:25:39 UTC"
  generator: scripts/generate_subsystem_readmes.py
  config: config/subsystems/readme_config.yaml
  time_verified: "worldtimeapi.org (drift: 1.5s)"
  auto_generated: true
---

# Graph Adapter

> **Tier:** INFRASTRUCTURE | **Path:** `graph_adapter` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                              Graph Adapter                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   graph_adapt   │ ───► │  Outbound   │                  │
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

Neo4j graph database adapter

**Purpose:** Adapts packet data to Neo4j graph nodes and relationships.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute graph adapter tasks
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
| `memory/` | Required dependency |

---

## Directory Layout

```
graph_adapter/
├── __init__.py
├── packet_node_adapter.py
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `packet_node_adapter.py` | Wraps a node function, ensuring its input/output a |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `GraphAdapterService`)
- **Functions:** `snake_case` (e.g., `process_graph_adapter_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `packet_node_adapter.py` — PacketNodeAdapter

```python
class PacketNodeAdapter:
    """Wraps a node function, ensuring its input/output are logged to memory"""

    # Key methods:

    def __init__(self, ...) -> None: ...

    async def __call__(self, ...) -> GraphState: ...

```

**Public Methods:** `__init__`, `__call__`

**Lines:** 56-113 in `packet_node_adapter.py`


---

## Data Models and Contracts


### Exported Symbols (`__all__`)

`PacketNodeAdapter`

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class GraphAdapterRequest(BaseModel):
    """Request model for graph_adapter operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class GraphAdapterResponse(BaseModel):
    """Response model for graph_adapter operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Graph operations are transactional**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Graph_Adapter components are discovered and registered.
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
# Graph_Adapter feature flags
L9_ENABLE_GRAPH_ADAPTER_TRACING: true  # Enable detailed tracing
L9_ENABLE_GRAPH_ADAPTER_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_GRAPH_ADAPTER_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
graph_adapter:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
GRAPH_ADAPTER_LOG_LEVEL=INFO
GRAPH_ADAPTER_TIMEOUT=30
GRAPH_ADAPTER_ENABLED=true
```

---

## API Surface (Public)

See key components for public API details.

### Usage Example

```python
from graph_adapter import GraphAdapterService

# Initialize
service = GraphAdapterService()

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

Graph Adapter operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-14T08:25:39Z",
  "level": "INFO",
  "module": "graph_adapter",
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
| `graph_adapter_operation_duration_ms` | Histogram | Operation latency distribution |
| `graph_adapter_operation_total` | Counter | Total operations processed |
| `graph_adapter_error_total` | Counter | Total errors encountered |
| `graph_adapter_active_connections` | Gauge | Current active connections |

### Tracing

Graph Adapter emits OpenTelemetry spans:

- `graph_adapter.execute` — Root span for operation
  - `graph_adapter.validate` — Input validation
  - `graph_adapter.process` — Core processing
  - `graph_adapter.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/graph_adapter/`:
- `test_graph_adapter.py` — Core unit tests
- `test_graph_adapter_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test graph_adapter with real dependencies
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

- `**/*.py` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- `__init__.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

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
