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

# Boundary Enforcement

> **Tier:** CORE | **Path:** `core/boundary` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                           Boundary Enforcement                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_bounda   │ ───► │  Outbound   │                  │
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

Module boundary and interface enforcement

**Purpose:** Enforces clean boundaries between subsystems.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core boundary tasks
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
core/boundary/
├── __init__.py
├── enforcer.py
```

| File          | Purpose                                            |
| ------------- | -------------------------------------------------- |
| `__init__.py` | Core module (PROTECTED)                            |
| `enforcer.py` | Parsed PRIVATE_BOUNDARY specification.             |
| `enforcer.py` | Stateful boundary enforcer with caching and config |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreBoundaryService`)
- **Functions:** `snake_case` (e.g., `process_core_boundary_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `enforcer.py` — BoundarySpec

```python
class BoundarySpec:
    """Parsed PRIVATE_BOUNDARY specification."""

    # Key methods:

    async def __init__(self, ...): ...

    async def apply_redactions(self, ...): ...

```

**Public Methods:** `__init__`, `apply_redactions`

**Lines:** 88-119 in `enforcer.py`

### `enforcer.py` — BoundaryEnforcer

```python
class BoundaryEnforcer:
    """Stateful boundary enforcer with caching and configuration."""

    # Key methods:

    async def __init__(self, ...): ...

    async def _load_spec(self, ...): ...

    async def reload_spec(self, ...): ...

    async def enforce(self, ...): ...

    async def enforce_dict(self, ...): ...

```

**Public Methods:** `__init__`, `_load_spec`, `reload_spec`, `enforce`, `enforce_dict`

**Lines:** 266-381 in `enforcer.py`

---

## Data Models and Contracts

Data models are defined in `schemas.py` or inline within service classes.

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CoreBoundaryRequest(BaseModel):
    """Request model for core_boundary operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreBoundaryResponse(BaseModel):
    """Response model for core_boundary operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Boundaries are validated at import time**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Boundary components are discovered and registered.
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
# Core_Boundary feature flags
L9_ENABLE_CORE_BOUNDARY_TRACING: true # Enable detailed tracing
L9_ENABLE_CORE_BOUNDARY_METRICS: true # Enable Prometheus metrics
L9_ENABLE_CORE_BOUNDARY_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
core_boundary:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_BOUNDARY_LOG_LEVEL=INFO
CORE_BOUNDARY_TIMEOUT=30
CORE_BOUNDARY_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def load_boundary_spec(boundary_file)`

Load the PRIVATE_BOUNDARY.md specification file.

- **File:** `enforcer.py:122`
- **Async:** No

#### `def parse_boundary_spec(content)`

Parse PRIVATE_BOUNDARY.md content into a BoundarySpec.

- **File:** `enforcer.py:145`
- **Async:** No

#### `def enforce_boundary(prompt, context)`

Apply PRIVATE_BOUNDARY enforcement to a prompt.

- **File:** `enforcer.py:173`
- **Async:** No

#### `def enforce_response_boundary(response, context)`

Apply PRIVATE_BOUNDARY enforcement to a response.

- **File:** `enforcer.py:211`
- **Async:** No

#### `def enforce_payload_boundary(payload, protected_fields)`

Apply PRIVATE_BOUNDARY enforcement to a payload dict.

- **File:** `enforcer.py:231`
- **Async:** No

### Usage Example

```python
from core.boundary import CoreBoundaryService

# Initialize
service = CoreBoundaryService()

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

Core Boundary operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "core.boundary",
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
| `core_boundary_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_boundary_operation_total`       | Counter   | Total operations processed     |
| `core_boundary_error_total`           | Counter   | Total errors encountered       |
| `core_boundary_active_connections`    | Gauge     | Current active connections     |

### Tracing

Core Boundary emits OpenTelemetry spans:

- `core_boundary.execute` — Root span for operation
  - `core_boundary.validate` — Input validation
  - `core_boundary.process` — Core processing
  - `core_boundary.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_boundary/`:

- `test_core_boundary.py` — Core unit tests
- `test_core_boundary_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_boundary with real dependencies
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
