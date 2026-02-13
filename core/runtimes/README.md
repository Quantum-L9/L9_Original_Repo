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

# Runtime Implementations

> **Tier:** CORE | **Path:** `core/runtimes` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                         Runtime Implementations                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_runtim   │ ───► │  Outbound   │                  │
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

Alternative runtime implementations

**Purpose:** Provides different runtime implementations for various contexts.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core runtimes tasks
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

| Module     | Purpose             |
| ---------- | ------------------- |
| `runtime/` | Required dependency |

---

## Directory Layout

```
core/runtimes/
├── __init__.py
├── react_runtime.py
```

| File               | Purpose                                            |
| ------------------ | -------------------------------------------------- |
| `__init__.py`      | Core module (PROTECTED)                            |
| `react_runtime.py` | Single step in ReAct loop.                         |
| `react_runtime.py` | ReAct (Reason + Act) runtime for agent task execut |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreRuntimesService`)
- **Functions:** `snake_case` (e.g., `process_core_runtimes_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `react_runtime.py` — ReActStep

```python
class ReActStep:
    """Single step in ReAct loop."""

    # Key methods:

    def __init__(self, ...): ...

```

**Public Methods:** `__init__`

**Lines:** 44-58 in `react_runtime.py`

### `react_runtime.py` — ReActRuntime

```python
class ReActRuntime:
    """ReAct (Reason + Act) runtime for agent task execution."""

    # Key methods:

    def __init__(self, ...): ...

    async def execute_task(self, ...) -> ExecutionResult: ...

    def _build_thought_context(self, ...) -> dict[str, Any]: ...

    def _duration_ms(self, ...) -> int: ...

```

**Public Methods:** `__init__`, `execute_task`, `_build_thought_context`, `_duration_ms`

**Lines:** 61-207 in `react_runtime.py`

---

## Data Models and Contracts

### Exported Symbols (`__all__`)

`ReActRuntime`, `ReActStep`, `create_react_runtime`

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CoreRuntimesRequest(BaseModel):
    """Request model for core_runtimes operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreRuntimesResponse(BaseModel):
    """Response model for core_runtimes operations."""
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

1. **Discovery:** Core_Runtimes components are discovered and registered.
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
# Core_Runtimes feature flags
L9_ENABLE_CORE_RUNTIMES_TRACING: true # Enable detailed tracing
L9_ENABLE_CORE_RUNTIMES_METRICS: true # Enable Prometheus metrics
L9_ENABLE_CORE_RUNTIMES_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
core_runtimes:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_RUNTIMES_LOG_LEVEL=INFO
CORE_RUNTIMES_TIMEOUT=30
CORE_RUNTIMES_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def create_react_runtime(aios_runtime, tool_registry) -> ReActRuntime`

Factory function to create ReAct runtime.

- **File:** `react_runtime.py:210`
- **Async:** No
- **Returns:** `ReActRuntime`

### Usage Example

```python
from core.runtimes import CoreRuntimesService

# Initialize
service = CoreRuntimesService()

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

Core Runtimes operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-29T03:05:45Z",
  "level": "INFO",
  "module": "core.runtimes",
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

| Metric                                | Type      | Description                    |
| ------------------------------------- | --------- | ------------------------------ |
| `core_runtimes_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_runtimes_operation_total`       | Counter   | Total operations processed     |
| `core_runtimes_error_total`           | Counter   | Total errors encountered       |
| `core_runtimes_active_connections`    | Gauge     | Current active connections     |

### Tracing

Core Runtimes emits OpenTelemetry spans:

- `core_runtimes.execute` — Root span for operation
  - `core_runtimes.validate` — Input validation
  - `core_runtimes.process` — Core processing
  - `core_runtimes.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_runtimes/`:

- `test_core_runtimes.py` — Core unit tests
- `test_core_runtimes_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_runtimes with real dependencies
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
