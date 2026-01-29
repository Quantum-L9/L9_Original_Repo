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

# Development Utilities

> **Tier:** INFRASTRUCTURE | **Path:** `dev` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                          Development Utilities                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │       dev       │ ───► │  Outbound   │                  │
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

Development-only utilities and tools

**Purpose:** Provides development-only tools not for production use.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute dev tasks
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
| — | No outbound dependencies |

---

## Directory Layout

```
dev/
├── __init__.py
├── tools/__init__.py
├── tools/global_state_audit.py
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `global_state_audit.py` | Component |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `DevService`)
- **Functions:** `snake_case` (e.g., `process_dev_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `global_state_audit.py` — GlobalStateVisitor

```python
class GlobalStateVisitor:
    """No description"""

    # Key methods:

    def __init__(self, ...): ...

    def visit_Assign(self, ...): ...

    def generic_visit(self, ...): ...

```

**Public Methods:** `__init__`, `visit_Assign`, `generic_visit`

**Lines:** 59-96 in `global_state_audit.py`


---

## Data Models and Contracts


### Module Constants

| Constant | Value | Line |
|----------|-------|------|
| `ROOT` | `Path(__file__).resolve().parents[2]` | 43 |

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DevRequest(BaseModel):
    """Request model for dev operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class DevResponse(BaseModel):
    """Response model for dev operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Dev tools never imported in production**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Dev components are discovered and registered.
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
# Dev feature flags
L9_ENABLE_DEV_TRACING: true  # Enable detailed tracing
L9_ENABLE_DEV_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_DEV_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
dev:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
DEV_LOG_LEVEL=INFO
DEV_TIMEOUT=30
DEV_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def iter_python_files() -> list[Path]`

No description

- **File:** `global_state_audit.py:46`
- **Async:** No
- **Returns:** `list[Path]`

#### `def main()`

No description

- **File:** `global_state_audit.py:99`
- **Async:** No


### Usage Example

```python
from dev import DevService

# Initialize
service = DevService()

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

Dev operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-29T03:05:45Z",
  "level": "INFO",
  "module": "dev",
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
| `dev_operation_duration_ms` | Histogram | Operation latency distribution |
| `dev_operation_total` | Counter | Total operations processed |
| `dev_error_total` | Counter | Total errors encountered |
| `dev_active_connections` | Gauge | Current active connections |

### Tracing

Dev emits OpenTelemetry spans:

- `dev.execute` — Root span for operation
  - `dev.validate` — Input validation
  - `dev.process` — Core processing
  - `dev.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/dev/`:
- `test_dev.py` — Core unit tests
- `test_dev_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test dev with real dependencies
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
