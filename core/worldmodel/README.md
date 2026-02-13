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

# World Model Core

> **Tier:** CORE | **Path:** `core/worldmodel` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                             World Model Core                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_worldm   │ ───► │  Outbound   │                  │
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

Core world model abstractions

**Purpose:** Provides core abstractions for world model representation.

**What depends on it:** `world_model/`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core worldmodel tasks
- **State management:** Maintain internal state with proper lifecycle
- **Logging:** Emit structured logs for all operations
- **Metrics:** Expose Prometheus-compatible metrics

### What This Module Does NOT Do

- **Authentication** — Handled by `api/auth.py`
- **External communication** — Handled by clients/adapters
- **Scheduling** — Handled by runtime/task_queue.py

### Inbound Dependencies

| Module         | Purpose          |
| -------------- | ---------------- |
| `world_model/` | Uses this module |

### Outbound Dependencies

| Module | Purpose                  |
| ------ | ------------------------ |
| —      | No outbound dependencies |

---

## Directory Layout

```
core/worldmodel/
├── __init__.py
├── insight_emitter.py
├── l9_schema.py
├── service.py
```

| File           | Purpose                                  |
| -------------- | ---------------------------------------- |
| `__init__.py`  | Core module (PROTECTED)                  |
| `service.py`   | Service for L9 world model operations.   |
| `l9_schema.py` | Types of entities in the L9 world model. |
| `l9_schema.py` | Types of infrastructure components.      |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreWorldmodelService`)
- **Functions:** `snake_case` (e.g., `process_core_worldmodel_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `service.py` — WorldModelService

```python
class WorldModelService:
    """Service for L9 world model operations."""

    # Key methods:

    def __init__(self, ...): ...

    async def initialize(self, ...) -> None: ...

    async def _initialize_agents(self, ...) -> None: ...

    async def _initialize_infrastructure(self, ...) -> None: ...

    async def _initialize_tools(self, ...) -> None: ...

```

**Public Methods:** `__init__`, `initialize`, `_initialize_agents`, `_initialize_infrastructure`, `_initialize_tools`

**Lines:** 66-623 in `service.py`

### `l9_schema.py` — EntityType

```python
class EntityType:
    """Types of entities in the L9 world model."""

    # Key methods:

```

**Lines:** 51-59 in `l9_schema.py`

### `l9_schema.py` — InfrastructureType

```python
class InfrastructureType:
    """Types of infrastructure components."""

    # Key methods:

```

**Lines:** 62-70 in `l9_schema.py`

### `l9_schema.py` — ToolCategory

```python
class ToolCategory:
    """Categories of tools."""

    # Key methods:

```

**Lines:** 73-82 in `l9_schema.py`

### `l9_schema.py` — ToolRiskLevel

```python
class ToolRiskLevel:
    """Risk levels for tools."""

    # Key methods:

```

**Lines:** 85-91 in `l9_schema.py`

---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`WorldModelService`** — Service for L9 world model operations.

### Exported Symbols (`__all__`)

`ConnectionStatus`, `EntityType`, `InfrastructureType`, `Insight`, `InsightEmitter`, `L9Agent`, `L9ExternalSystem`, `L9Infrastructure`, `L9MemorySegment`, `L9Relationship`

_...and 8 more_

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CoreWorldmodelRequest(BaseModel):
    """Request model for core_worldmodel operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreWorldmodelResponse(BaseModel):
    """Response model for core_worldmodel operations."""
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

1. **Discovery:** Core_Worldmodel components are discovered and registered.
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
# Core_Worldmodel feature flags
L9_ENABLE_CORE_WORLDMODEL_TRACING: true # Enable detailed tracing
L9_ENABLE_CORE_WORLDMODEL_METRICS: true # Enable Prometheus metrics
L9_ENABLE_CORE_WORLDMODEL_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
core_worldmodel:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_WORLDMODEL_LOG_LEVEL=INFO
CORE_WORLDMODEL_TIMEOUT=30
CORE_WORLDMODEL_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def get_world_model_service(substrate_service) -> WorldModelService`

Get or create the global WorldModelService instance.

- **File:** `service.py:633`
- **Async:** No
- **Returns:** `WorldModelService`

#### `def get_insight_emitter(substrate_service) -> InsightEmitter`

Get or create the global InsightEmitter instance.

- **File:** `insight_emitter.py:366`
- **Async:** No
- **Returns:** `InsightEmitter`

### Usage Example

```python
from core.worldmodel import CoreWorldmodelService

# Initialize
service = CoreWorldmodelService()

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

Core Worldmodel operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-29T03:05:45Z",
  "level": "INFO",
  "module": "core.worldmodel",
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

| Metric                                  | Type      | Description                    |
| --------------------------------------- | --------- | ------------------------------ |
| `core_worldmodel_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_worldmodel_operation_total`       | Counter   | Total operations processed     |
| `core_worldmodel_error_total`           | Counter   | Total errors encountered       |
| `core_worldmodel_active_connections`    | Gauge     | Current active connections     |

### Tracing

Core Worldmodel emits OpenTelemetry spans:

- `core_worldmodel.execute` — Root span for operation
  - `core_worldmodel.validate` — Input validation
  - `core_worldmodel.process` — Core processing
  - `core_worldmodel.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_worldmodel/`:

- `test_core_worldmodel.py` — Core unit tests
- `test_core_worldmodel_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_worldmodel with real dependencies
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
