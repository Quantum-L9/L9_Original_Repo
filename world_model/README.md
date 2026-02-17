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

# World Model

> **Tier:** SERVICES | **Path:** `world_model` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                               World Model                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   world_model   │ ───► │  Outbound   │                  │
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

Causal graph, knowledge engine, and world state management

**Purpose:** Maintains causal knowledge graph and world state for agent reasoning.

**What depends on it:** `orchestrators/world_model/`, `core/agents/`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute world model tasks
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
| `orchestrators/world_model/` | Uses this module |
| `core/agents/` | Uses this module |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| `memory/substrate_service.py` | Required dependency |

---

## Directory Layout

```
world_model/
├── __init__.py
├── _pack_staging/loader.py
├── _pack_staging/neo4j_substrate.py
├── _pack_staging/orchestrator.py
├── _pack_staging/postgres_substrate.py
├── _pack_staging/query_engine.py
├── _pack_staging/redis_substrate.py
├── _pack_staging/registry.py
├── _pack_staging/state.py
├── _pack_staging/test_integration.py
├── _pack_staging/updater.py
├── causal_graph.py
├── causal_mapper.py
├── engine.py
├── interfaces.py
└── ... (15 more files)
```

| File | Purpose |
|------|---------|
| `engine.py` | Core module (PROTECTED) |
| `service.py` | Core module (PROTECTED) |
| `__init__.py` | Core module (PROTECTED) |
| `interfaces.py` | Interface for World Model State management. |
| `interfaces.py` | Interface for World Model Engine. |
| `interfaces.py` | Interface for World Model Updater. |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `WorldModelService`)
- **Functions:** `snake_case` (e.g., `process_world_model_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `interfaces.py` — IWorldModelState

```python
class IWorldModelState:
    """Interface for World Model State management."""

    # Key methods:

    def get_entity(self, ...) -> dict[str, Any] | None: ...

    def get_relations(self, ...) -> list[dict[str, Any]]: ...

    def snapshot(self, ...) -> dict[str, Any]: ...

    def restore(self, ...) -> None: ...

```

**Public Methods:** `get_entity`, `get_relations`, `snapshot`, `restore`

**Lines:** 53-84 in `interfaces.py`

### `interfaces.py` — IWorldModelEngine

```python
class IWorldModelEngine:
    """Interface for World Model Engine."""

    # Key methods:

    def load_specs(self, ...) -> None: ...

    def initialize_state(self, ...) -> None: ...

    def update_from_packet(self, ...) -> dict[str, Any]: ...

    def query(self, ...) -> dict[str, Any]: ...

    def simulate(self, ...) -> dict[str, Any]: ...

```

**Public Methods:** `load_specs`, `initialize_state`, `update_from_packet`, `query`, `simulate`

**Lines:** 87-148 in `interfaces.py`

### `interfaces.py` — IWorldModelUpdater

```python
class IWorldModelUpdater:
    """Interface for World Model Updater."""

    # Key methods:

    def validate_update(self, ...) -> bool: ...

    def apply_update(self, ...) -> dict[str, Any]: ...

```

**Public Methods:** `validate_update`, `apply_update`

**Lines:** 151-188 in `interfaces.py`

### `interfaces.py` — ICausalGraph

```python
class ICausalGraph:
    """Interface for Causal Graph operations."""

    # Key methods:

    def get_causes(self, ...) -> list[str]: ...

    def get_effects(self, ...) -> list[str]: ...

    def query_path(self, ...) -> list[str]: ...

```

**Public Methods:** `get_causes`, `get_effects`, `query_path`

**Lines:** 191-219 in `interfaces.py`

### `interfaces.py` — IWorldModelLoader

```python
class IWorldModelLoader:
    """Interface for World Model Loader."""

    # Key methods:

    def load_yaml(self, ...) -> dict[str, Any]: ...

    def load_entity_schemas(self, ...) -> dict[str, Any]: ...

    def load_relation_schemas(self, ...) -> dict[str, Any]: ...

    def load_causal_structure(self, ...) -> dict[str, Any]: ...

```

**Public Methods:** `load_yaml`, `load_entity_schemas`, `load_relation_schemas`, `load_causal_structure`

**Lines:** 222-253 in `interfaces.py`


---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`IWorldModelState`** — Interface for World Model State management.
- **`IWorldModelEngine`** — Interface for World Model Engine.
- **`IWorldModelUpdater`** — Interface for World Model Updater.

### Exported Symbols (`__all__`)

`CausalLink`, `CausalMapper`, `CausalNode`, `CausalPath`, `CausalQueryResult`, `CausalRelationType`, `CausalStrength`, `ConstraintSet`, `Decision`, `Entity`

*...and 41 more*

### Module Constants

| Constant | Value | Line |
|----------|-------|------|
| `SUPPORTED_PACKET_TYPES` | `frozenset(['ir_graph', 'execution_plan',...` | 98 |
| `PACKET_TYPE_IR_GRAPH` | `'ir_graph'` | 88 |
| `PACKET_TYPE_EXECUTION_PLAN` | `'execution_plan'` | 89 |
| `PACKET_TYPE_REFLECTION` | `'reflection'` | 90 |
| `PACKET_TYPE_INSIGHT` | `'insight'` | 91 |
| `PACKET_TYPE_EVENT` | `'event'` | 92 |
| `PACKET_TYPE_MEMORY_WRITE` | `'memory_write'` | 93 |
| `PACKET_TYPE_REASONING_TRACE` | `'reasoning_trace'` | 94 |

*...and 2 more constants*

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class WorldModelRequest(BaseModel):
    """Request model for world_model operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class WorldModelResponse(BaseModel):
    """Response model for world_model operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Causal relationships are directional**
- **World state is versioned**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** World_Model components are discovered and registered.
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
# World_Model feature flags
L9_ENABLE_WORLD_MODEL_TRACING: true  # Enable detailed tracing
L9_ENABLE_WORLD_MODEL_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_WORLD_MODEL_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
world_model:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
WORLD_MODEL_LOG_LEVEL=INFO
WORLD_MODEL_TIMEOUT=30
WORLD_MODEL_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def get_world_model_service(service) -> WorldModelService`

Get world model service singleton, or use injected instance.

- **File:** `service.py:665`
- **Async:** No
- **Returns:** `WorldModelService`

#### `async def close_world_model_service()`

Close service and cleanup.

- **File:** `service.py:690`
- **Async:** Yes

#### `def get_world_model_service_api(engine, runtime) -> WorldModelServiceAPI`

Get or create singleton service API.

- **File:** `world_model_service.py:936`
- **Async:** No
- **Returns:** `WorldModelServiceAPI`

#### `def reset_world_model_service_api() -> None`

Reset the singleton service API.

- **File:** `world_model_service.py:962`
- **Async:** No
- **Returns:** `None`

#### `async def create_runtime_with_substrate(substrate_service, engine, config) -> WorldModelRuntime`

Create a WorldModelRuntime wired to the Memory Substrate.

- **File:** `runtime.py:2009`
- **Async:** Yes
- **Returns:** `WorldModelRuntime`


### Usage Example

```python
from world_model import WorldModelService

# Initialize
service = WorldModelService()

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

World Model operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-17T00:14:44Z",
  "level": "INFO",
  "module": "world_model",
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
| `world_model_operation_duration_ms` | Histogram | Operation latency distribution |
| `world_model_operation_total` | Counter | Total operations processed |
| `world_model_error_total` | Counter | Total errors encountered |
| `world_model_active_connections` | Gauge | Current active connections |

### Tracing

World Model emits OpenTelemetry spans:

- `world_model.execute` — Root span for operation
  - `world_model.validate` — Input validation
  - `world_model.process` — Core processing
  - `world_model.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/world_model/`:
- `test_world_model.py` — Core unit tests
- `test_world_model_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test world_model with real dependencies
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

- `causal_graph.py` — Application logic, safe to modify
- `causal_mapper.py` — Application logic, safe to modify
- `knowledge_ingestor.py` — Application logic, safe to modify
- `query_engine.py` — Application logic, safe to modify
- `nodes/**` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- `engine.py` — Requires human review before merge
- `service.py` — Requires human review before merge
- `__init__.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `engine.py` — PROTECTED: Changes break system invariants
- `service.py` — PROTECTED: Changes break system invariants
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
