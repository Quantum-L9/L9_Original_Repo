---
dora:
  version: "1.0"
  type: subsystem_readme
  generated: "2026-01-29 03:05:45 UTC"
  generator: scripts/generate_subsystem_readmes.py
  config: config/subsystems/readme_config.yaml
  time_verified: "system clock (verification skipped)"
  auto_generated: true
---

# Integration Layer

> **Tier:** CORE | **Path:** `core/integration` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                            Integration Layer                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_integr   │ ───► │  Outbound   │                  │
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

Cross-subsystem integration utilities

**Purpose:** Facilitates integration between subsystems.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core integration tasks
- **State management:** Maintain internal state with proper lifecycle
- **Logging:** Emit structured logs for all operations
- **Metrics:** Expose Prometheus-compatible metrics

### What This Module Does NOT Do

- **Authentication** — Handled by `api/auth.py`
- **External communication** — Handled by clients/adapters
- **Scheduling** — Handled by runtime/task_queue.py

### Inbound Dependencies

| Module | Purpose                 |
| ------ | ----------------------- |
| —      | No inbound dependencies |

### Outbound Dependencies

| Module | Purpose                  |
| ------ | ------------------------ |
| —      | No outbound dependencies |

---

## Directory Layout

```
core/integration/
├── __init__.py
├── graph_to_wm_sync.py
├── tool_pattern_extractor.py
├── wm_to_graph_sync.py
```

| File                        | Purpose                                            |
| --------------------------- | -------------------------------------------------- |
| `__init__.py`               | Core module (PROTECTED)                            |
| `graph_to_wm_sync.py`       | Service to sync agent state from Neo4j to World Mo |
| `tool_pattern_extractor.py` | Service to extract tool usage patterns and feed to |
| `wm_to_graph_sync.py`       | Syncs World Model causal data to Neo4j graph.      |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreIntegrationService`)
- **Functions:** `snake_case` (e.g., `process_core_integration_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `graph_to_wm_sync.py` — GraphToWorldModelSync

```python
class GraphToWorldModelSync:
    """Service to sync agent state from Neo4j to World Model."""

    # Key methods:

    def __init__(self, ...): ...

    async def start(self, ...) -> None: ...

    async def stop(self, ...) -> None: ...

    async def _sync_loop(self, ...) -> None: ...

    async def sync_agent(self, ...) -> dict[str, Any]: ...

```

**Public Methods:** `__init__`, `start`, `stop`, `_sync_loop`, `sync_agent`

**Lines:** 62-343 in `graph_to_wm_sync.py`

### `tool_pattern_extractor.py` — ToolPatternExtractor

```python
class ToolPatternExtractor:
    """Service to extract tool usage patterns and feed to World Model."""

    # Key methods:

    def __init__(self, ...): ...

    async def start(self, ...) -> None: ...

    async def stop(self, ...) -> None: ...

    async def _extraction_loop(self, ...) -> None: ...

    async def run_extraction(self, ...) -> dict[str, Any]: ...

```

**Public Methods:** `__init__`, `start`, `stop`, `_extraction_loop`, `run_extraction`

**Lines:** 66-429 in `tool_pattern_extractor.py`

### `wm_to_graph_sync.py` — WMToGraphSync

```python
class WMToGraphSync:
    """Syncs World Model causal data to Neo4j graph."""

    # Key methods:

    def __init__(self, ...): ...

    async def start(self, ...) -> None: ...

    async def stop(self, ...) -> None: ...

    async def _sync_loop(self, ...) -> None: ...

    async def sync_all(self, ...) -> dict[str, int]: ...

```

**Public Methods:** `__init__`, `start`, `stop`, `_sync_loop`, `sync_all`

**Lines:** 66-304 in `wm_to_graph_sync.py`

---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`GraphToWorldModelSync`** — Service to sync agent state from Neo4j to World Model.

### Exported Symbols (`__all__`)

`GraphToWorldModelSync`, `ToolPatternExtractor`, `WMToGraphSync`, `start_wm_graph_sync`, `stop_wm_graph_sync`

### Module Constants

| Constant                            | Value                                         | Line |
| ----------------------------------- | --------------------------------------------- | ---- |
| `L9_GRAPH_WM_SYNC`                  | `os.getenv('L9_GRAPH_WM_SYNC', 'true').lo...` | 59   |
| `L9_TOOL_PATTERN_EXTRACTION`        | `os.getenv('L9_TOOL_PATTERN_EXTRACTION', ...` | 58   |
| `DEFAULT_EXTRACTION_INTERVAL_HOURS` | `6`                                           | 63   |
| `L9_WM_GRAPH_SYNC`                  | `os.getenv('L9_WM_GRAPH_SYNC', 'true').lo...` | 63   |

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CoreIntegrationRequest(BaseModel):
    """Request model for core_integration operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreIntegrationResponse(BaseModel):
    """Response model for core_integration operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **All operations must be idempotent**
- **State changes logged to audit trail**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Integration components are discovered and registered.
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
# Core_Integration feature flags
L9_ENABLE_CORE_INTEGRATION_TRACING: true # Enable detailed tracing
L9_ENABLE_CORE_INTEGRATION_METRICS: true # Enable Prometheus metrics
L9_ENABLE_CORE_INTEGRATION_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
core_integration:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_INTEGRATION_LOG_LEVEL=INFO
CORE_INTEGRATION_TIMEOUT=30
CORE_INTEGRATION_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def get_graph_wm_sync(neo4j_driver) -> GraphToWorldModelSync`

Get the global GraphToWorldModelSync instance.

- **File:** `graph_to_wm_sync.py:350`
- **Async:** No
- **Returns:** `GraphToWorldModelSync`

#### `async def start_graph_wm_sync(neo4j_driver) -> None`

Start the global sync service.

- **File:** `graph_to_wm_sync.py:365`
- **Async:** Yes
- **Returns:** `None`

#### `async def stop_graph_wm_sync() -> None`

Stop the global sync service.

- **File:** `graph_to_wm_sync.py:378`
- **Async:** Yes
- **Returns:** `None`

#### `def get_tool_pattern_extractor() -> ToolPatternExtractor`

Get the global ToolPatternExtractor instance.

- **File:** `tool_pattern_extractor.py:436`
- **Async:** No
- **Returns:** `ToolPatternExtractor`

#### `async def start_tool_pattern_extraction() -> None`

Start the global extractor.

- **File:** `tool_pattern_extractor.py:444`
- **Async:** Yes
- **Returns:** `None`

### Usage Example

```python
from core.integration import CoreIntegrationService

# Initialize
service = CoreIntegrationService()

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

Core Integration operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-29T03:05:45Z",
  "level": "INFO",
  "module": "core.integration",
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

| Metric                                   | Type      | Description                    |
| ---------------------------------------- | --------- | ------------------------------ |
| `core_integration_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_integration_operation_total`       | Counter   | Total operations processed     |
| `core_integration_error_total`           | Counter   | Total errors encountered       |
| `core_integration_active_connections`    | Gauge     | Current active connections     |

### Tracing

Core Integration emits OpenTelemetry spans:

- `core_integration.execute` — Root span for operation
  - `core_integration.validate` — Input validation
  - `core_integration.process` — Core processing
  - `core_integration.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_integration/`:

- `test_core_integration.py` — Core unit tests
- `test_core_integration_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_integration with real dependencies
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
