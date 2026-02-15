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

# Dependency Injection

> **Tier:** CORE | **Path:** `core/di` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                           Dependency Injection                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │     core_di     │ ───► │  Outbound   │                  │
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

Dependency injection container and utilities

**Purpose:** Provides DI container for loose coupling and testability.

**What depends on it:** `config/di_config.py`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core di tasks
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
| `config/di_config.py` | Uses this module |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| — | No outbound dependencies |

---

## Directory Layout

```
core/di/
├── __init__.py
├── bootstrap.py
├── bootstrap_integration.py
├── container.py
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `container.py` | Core module (PROTECTED) |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreDiService`)
- **Functions:** `snake_case` (e.g., `process_core_di_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `container.py` — DIContainerError

```python
class DIContainerError:
    """Base exception for DI container errors."""

    # Key methods:

```

**Lines:** 75-78 in `container.py`

### `container.py` — CircularDependencyError

```python
class CircularDependencyError:
    """Raised when circular dependency is detected."""

    # Key methods:

```

**Lines:** 81-84 in `container.py`

### `container.py` — BindingNotFoundError

```python
class BindingNotFoundError:
    """Raised when no binding exists for requested type."""

    # Key methods:

```

**Lines:** 87-90 in `container.py`

### `container.py` — ResolutionError

```python
class ResolutionError:
    """Raised when dependency resolution fails."""

    # Key methods:

```

**Lines:** 93-96 in `container.py`

### `container.py` — DIContainer

```python
class DIContainer:
    """Lightweight dependency injection container for L9."""

    # Key methods:

    def __init__(self, ...): ...

    def bind_singleton(self, ...) -> None: ...

    def bind_transient(self, ...) -> None: ...

    def bind_instance(self, ...) -> None: ...

    def resolve(self, ...) -> T: ...

```

**Public Methods:** `__init__`, `bind_singleton`, `bind_transient`, `bind_instance`, `resolve`

**Lines:** 99-535 in `container.py`


---

## Data Models and Contracts


### Exported Symbols (`__all__`)

`BindingNotFoundError`, `CircularDependencyError`, `DIContainer`, `DIContainerError`, `MemorySubstrateContainer`, `ResolutionError`, `bootstrap_di_container`, `get_container`, `get_di_container`, `reset_di_container`

*...and 1 more*

### Module Constants

| Constant | Value | Line |
|----------|-------|------|
| `T` | `TypeVar('T')` | 72 |

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class CoreDiRequest(BaseModel):
    """Request model for core_di operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreDiResponse(BaseModel):
    """Response model for core_di operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Container is singleton per process**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Di components are discovered and registered.
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
# Core_Di feature flags
L9_ENABLE_CORE_DI_TRACING: true  # Enable detailed tracing
L9_ENABLE_CORE_DI_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_CORE_DI_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
core_di:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_DI_LOG_LEVEL=INFO
CORE_DI_TIMEOUT=30
CORE_DI_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def bootstrap_di_container(container) -> dict[str, int]`

Bootstrap DIContainer with all core service registrations.

- **File:** `bootstrap.py:59`
- **Async:** No
- **Returns:** `dict[str, int]`

#### `def get_di_container() -> DIContainer`

Get global DI container instance.

- **File:** `container.py:543`
- **Async:** No
- **Returns:** `DIContainer`

#### `def reset_di_container() -> None`

Reset global DI container.

- **File:** `container.py:563`
- **Async:** No
- **Returns:** `None`

#### `async def bootstrap_di_container() -> DIContainer`

Bootstrap the DI container with all core services.

- **File:** `bootstrap_integration.py:55`
- **Async:** Yes
- **Returns:** `DIContainer`

#### `async def shutdown_di_container() -> None`

Shutdown the DI container and cleanup resources.

- **File:** `bootstrap_integration.py:271`
- **Async:** Yes
- **Returns:** `None`


### Usage Example

```python
from core.di import CoreDiService

# Initialize
service = CoreDiService()

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

Core Di operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-14T08:25:39Z",
  "level": "INFO",
  "module": "core.di",
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
| `core_di_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_di_operation_total` | Counter | Total operations processed |
| `core_di_error_total` | Counter | Total errors encountered |
| `core_di_active_connections` | Gauge | Current active connections |

### Tracing

Core Di emits OpenTelemetry spans:

- `core_di.execute` — Root span for operation
  - `core_di.validate` — Input validation
  - `core_di.process` — Core processing
  - `core_di.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_di/`:
- `test_core_di.py` — Core unit tests
- `test_core_di_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_di with real dependencies
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
- `container.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `__init__.py` — PROTECTED: Changes break system invariants
- `container.py` — PROTECTED: Changes break system invariants

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
