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

# Resilience Patterns

> **Tier:** CORE | **Path:** `core/resilience` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                           Resilience Patterns                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_resili   │ ───► │  Outbound   │                  │
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

Circuit breakers, retry logic, and fault tolerance

**Purpose:** Implements circuit breakers, retry logic, and fault tolerance patterns.

**What depends on it:** `runtime/`, `core/agents/`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core resilience tasks
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
| `runtime/` | Uses this module |
| `core/agents/` | Uses this module |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| — | No outbound dependencies |

---

## Directory Layout

```
core/resilience/
├── __init__.py
├── mixin.py
├── protocols.py
├── retry.py
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `mixin.py` | Mixin providing standard retry + circuit breaker + |
| `protocols.py` | Protocol for services that support resilience patt |
| `retry.py` | Raised when all retry attempts have been exhausted |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreResilienceService`)
- **Functions:** `snake_case` (e.g., `process_core_resilience_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `mixin.py` — ResilienceMixin

```python
class ResilienceMixin:
    """Mixin providing standard retry + circuit breaker + DLQ behavior."""

    # Key methods:

    async def with_resilience(self, ...) -> Any: ...

```

**Public Methods:** `with_resilience`

**Lines:** 69-226 in `mixin.py`

### `protocols.py` — ResilientService

```python
class ResilientService:
    """Protocol for services that support resilience patterns."""

    # Key methods:

```

**Lines:** 51-70 in `protocols.py`

### `retry.py` — RetryExhaustedError

```python
class RetryExhaustedError:
    """Raised when all retry attempts have been exhausted."""

    # Key methods:

    def __init__(self, ...): ...

```

**Public Methods:** `__init__`

**Lines:** 70-86 in `retry.py`

### `retry.py` — AsyncRetryConfig

```python
class AsyncRetryConfig:
    """Configuration for async retry behavior."""

    # Key methods:

    def calculate_delay(self, ...) -> float: ...

```

**Public Methods:** `calculate_delay`

**Lines:** 90-116 in `retry.py`


---

## Data Models and Contracts


### Exported Symbols (`__all__`)

`AsyncRetryConfig`, `ResilienceMixin`, `ResilientService`, `RetryExhaustedError`, `async_retry`

### Module Constants

| Constant | Value | Line |
|----------|-------|------|
| `T` | `TypeVar('T')` | 67 |
| `DEFAULT_RETRY_CONFIG` | `AsyncRetryConfig()` | 120 |

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class CoreResilienceRequest(BaseModel):
    """Request model for core_resilience operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreResilienceResponse(BaseModel):
    """Response model for core_resilience operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Circuit breakers have configurable thresholds**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Resilience components are discovered and registered.
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
# Core_Resilience feature flags
L9_ENABLE_CORE_RESILIENCE_TRACING: true  # Enable detailed tracing
L9_ENABLE_CORE_RESILIENCE_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_CORE_RESILIENCE_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
core_resilience:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_RESILIENCE_LOG_LEVEL=INFO
CORE_RESILIENCE_TIMEOUT=30
CORE_RESILIENCE_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `async def async_retry(coro_func) -> T`

Execute async function with retry logic and exponential backoff.

- **File:** `retry.py:124`
- **Async:** Yes
- **Returns:** `T`


### Usage Example

```python
from core.resilience import CoreResilienceService

# Initialize
service = CoreResilienceService()

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

Core Resilience operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-14T08:25:39Z",
  "level": "INFO",
  "module": "core.resilience",
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
| `core_resilience_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_resilience_operation_total` | Counter | Total operations processed |
| `core_resilience_error_total` | Counter | Total errors encountered |
| `core_resilience_active_connections` | Gauge | Current active connections |

### Tracing

Core Resilience emits OpenTelemetry spans:

- `core_resilience.execute` — Root span for operation
  - `core_resilience.validate` — Input validation
  - `core_resilience.process` — Core processing
  - `core_resilience.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_resilience/`:
- `test_core_resilience.py` — Core unit tests
- `test_core_resilience_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_resilience with real dependencies
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
