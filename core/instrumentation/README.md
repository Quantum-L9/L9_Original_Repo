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

# Instrumentation

> **Tier:** CORE | **Path:** `core/instrumentation` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                             Instrumentation                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_instru   │ ───► │  Outbound   │                  │
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

Code instrumentation for observability

**Purpose:** Instruments code for metrics, tracing, and logging.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core instrumentation tasks
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

| Module                | Purpose             |
| --------------------- | ------------------- |
| `core/observability/` | Required dependency |

---

## Directory Layout

```
core/instrumentation/
├── __init__.py
├── decorators.py
```

| File          | Purpose                 |
| ------------- | ----------------------- |
| `__init__.py` | Core module (PROTECTED) |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreInstrumentationService`)
- **Functions:** `snake_case` (e.g., `process_core_instrumentation_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

See source files for component details.

---

## Data Models and Contracts

See source files for data model definitions.

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CoreInstrumentationRequest(BaseModel):
    """Request model for core_instrumentation operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreInstrumentationResponse(BaseModel):
    """Response model for core_instrumentation operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Instrumentation has minimal overhead**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Instrumentation components are discovered and registered.
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
# Core_Instrumentation feature flags
L9_ENABLE_CORE_INSTRUMENTATION_TRACING: true # Enable detailed tracing
L9_ENABLE_CORE_INSTRUMENTATION_METRICS: true # Enable Prometheus metrics
L9_ENABLE_CORE_INSTRUMENTATION_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
core_instrumentation:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_INSTRUMENTATION_LOG_LEVEL=INFO
CORE_INSTRUMENTATION_TIMEOUT=30
CORE_INSTRUMENTATION_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def get_current_trace_id()`

Get current trace_id from context.

- **File:** `decorators.py:72`
- **Async:** No

#### `def set_trace_id(trace_id)`

Set trace_id in current context.

- **File:** `decorators.py:87`
- **Async:** No

#### `def get_current_correlation_id()`

Get current correlation_id from context.

- **File:** `decorators.py:101`
- **Async:** No

#### `def set_correlation_id(correlation_id)`

Set correlation_id in current context.

- **File:** `decorators.py:111`
- **Async:** No

#### `def capture_source_location(frame)`

Capture source code location from call stack.

- **File:** `decorators.py:126`
- **Async:** No

### Usage Example

```python
from core.instrumentation import CoreInstrumentationService

# Initialize
service = CoreInstrumentationService()

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

Core Instrumentation operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "core.instrumentation",
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

| Metric                                       | Type      | Description                    |
| -------------------------------------------- | --------- | ------------------------------ |
| `core_instrumentation_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_instrumentation_operation_total`       | Counter   | Total operations processed     |
| `core_instrumentation_error_total`           | Counter   | Total errors encountered       |
| `core_instrumentation_active_connections`    | Gauge     | Current active connections     |

### Tracing

Core Instrumentation emits OpenTelemetry spans:

- `core_instrumentation.execute` — Root span for operation
  - `core_instrumentation.validate` — Input validation
  - `core_instrumentation.process` — Core processing
  - `core_instrumentation.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_instrumentation/`:

- `test_core_instrumentation.py` — Core unit tests
- `test_core_instrumentation_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_instrumentation with real dependencies
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
