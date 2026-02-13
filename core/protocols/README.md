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

# Abstract Protocols

> **Tier:** CORE | **Path:** `core/protocols` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                            Abstract Protocols                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_protoc   │ ───► │  Outbound   │                  │
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

Protocol definitions and abstract interfaces

**Purpose:** Defines abstract protocols for dependency injection and loose coupling.

**What depends on it:** `all modules`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core protocols tasks
- **State management:** Maintain internal state with proper lifecycle
- **Logging:** Emit structured logs for all operations
- **Metrics:** Expose Prometheus-compatible metrics

### What This Module Does NOT Do

- **Authentication** — Handled by `api/auth.py`
- **External communication** — Handled by clients/adapters
- **Scheduling** — Handled by runtime/task_queue.py

### Inbound Dependencies

| Module        | Purpose          |
| ------------- | ---------------- |
| `all modules` | Uses this module |

### Outbound Dependencies

| Module | Purpose                  |
| ------ | ------------------------ |
| —      | No outbound dependencies |

---

## Directory Layout

```
core/protocols/
├── __init__.py
├── agent_protocols.py
├── connection_protocols.py
├── error_handling_protocols.py
├── kernel_protocols.py
├── memory_protocols.py
├── observability_protocols.py
├── rate_limiting_protocols.py
├── retry_protocols.py
├── secrets_protocols.py
├── service_protocols.py
├── substrate_protocols.py
├── validation_protocols.py
```

| File                         | Purpose                                         |
| ---------------------------- | ----------------------------------------------- |
| `__init__.py`                | Core module (PROTECTED)                         |
| `observability_protocols.py` | Span kind enumeration.                          |
| `observability_protocols.py` | Span status enumeration.                        |
| `observability_protocols.py` | Protocol for distributed tracing span emission. |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreProtocolsService`)
- **Functions:** `snake_case` (e.g., `process_core_protocols_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `observability_protocols.py` — SpanKind

```python
class SpanKind:
    """Span kind enumeration."""

    # Key methods:

```

**Lines:** 59-68 in `observability_protocols.py`

### `observability_protocols.py` — SpanStatus

```python
class SpanStatus:
    """Span status enumeration."""

    # Key methods:

```

**Lines:** 71-76 in `observability_protocols.py`

### `observability_protocols.py` — SpanEmitter

```python
class SpanEmitter:
    """Protocol for distributed tracing span emission."""

    # Key methods:

    def start_span(self, ...) -> Any: ...

    def finish_span(self, ...) -> None: ...

    def emit_span(self, ...) -> None: ...

    def add_span_event(self, ...) -> None: ...

```

**Public Methods:** `start_span`, `finish_span`, `emit_span`, `add_span_event`

**Lines:** 80-152 in `observability_protocols.py`

### `observability_protocols.py` — MetricsCollector

```python
class MetricsCollector:
    """Protocol for metrics collection and aggregation."""

    # Key methods:

    def increment_counter(self, ...) -> None: ...

    def set_gauge(self, ...) -> None: ...

    def record_histogram(self, ...) -> None: ...

    def get_metrics(self, ...) -> dict[str, Any]: ...

```

**Public Methods:** `increment_counter`, `set_gauge`, `record_histogram`, `get_metrics`

**Lines:** 156-215 in `observability_protocols.py`

### `observability_protocols.py` — TraceContext

```python
class TraceContext:
    """Protocol for trace context propagation."""

    # Key methods:

    def trace_id(self, ...) -> str: ...

    def span_id(self, ...) -> str: ...

    def parent_span_id(self, ...) -> str | None: ...

    def to_headers(self, ...) -> dict[str, str]: ...

    def from_headers(self, ...) -> TraceContext: ...

```

**Public Methods:** `trace_id`, `span_id`, `parent_span_id`, `to_headers`, `from_headers`

**Lines:** 219-267 in `observability_protocols.py`

---

## Data Models and Contracts

### Exported Symbols (`__all__`)

`ActivatableAgent`, `AgentContext`, `AgentOrchestrator`, `AgentRegistry`, `AgentState`, `BackoffStrategy`, `CacheClient`, `ConnectionPoolProtocol`, `ConnectionProtocol`, `ConnectionState`

_...and 52 more_

### Module Constants

| Constant | Value                                    | Line |
| -------- | ---------------------------------------- | ---- |
| `T`      | `TypeVar('T')`                           | 44   |
| `P`      | `TypeVar('P')`                           | 45   |
| `T`      | `TypeVar('T', bound=Callable[..., Any])` | 534  |

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CoreProtocolsRequest(BaseModel):
    """Request model for core_protocols operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreProtocolsResponse(BaseModel):
    """Response model for core_protocols operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Protocols are abstract (no implementation)**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Protocols components are discovered and registered.
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
# Core_Protocols feature flags
L9_ENABLE_CORE_PROTOCOLS_TRACING: true # Enable detailed tracing
L9_ENABLE_CORE_PROTOCOLS_METRICS: true # Enable Prometheus metrics
L9_ENABLE_CORE_PROTOCOLS_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
core_protocols:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_PROTOCOLS_LOG_LEVEL=INFO
CORE_PROTOCOLS_TIMEOUT=30
CORE_PROTOCOLS_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def with_retry(policy) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]`

Decorator for async functions to add automatic retry behavior.

- **File:** `retry_protocols.py:340`
- **Async:** No
- **Returns:** `Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]`

#### `async def with_error_handling(handler, max_retries, backoff_factor, correlation_id, metadata)`

Async context manager for error handling with automatic retry logic.

- **File:** `error_handling_protocols.py:458`
- **Async:** Yes

#### `def validate_input(schema, validator) -> Callable[[T], T]`

Decorator for automatic input validation of async functions.

- **File:** `validation_protocols.py:537`
- **Async:** No
- **Returns:** `Callable[[T], T]`

#### `def rate_limited(key_func, policy) -> Callable[[Callable[..., Coroutine[Any, Any, Any]]], Callable[..., Coroutine[Any, Any, Any]]]`

Decorator for applying rate limiting to async functions.

- **File:** `rate_limiting_protocols.py:469`
- **Async:** No
- **Returns:** `Callable[[Callable[..., Coroutine[Any, Any, Any]]], Callable[..., Coroutine[Any, Any, Any]]]`

### Usage Example

```python
from core.protocols import CoreProtocolsService

# Initialize
service = CoreProtocolsService()

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

Core Protocols operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-29T03:05:45Z",
  "level": "INFO",
  "module": "core.protocols",
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

| Metric                                 | Type      | Description                    |
| -------------------------------------- | --------- | ------------------------------ |
| `core_protocols_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_protocols_operation_total`       | Counter   | Total operations processed     |
| `core_protocols_error_total`           | Counter   | Total errors encountered       |
| `core_protocols_active_connections`    | Gauge     | Current active connections     |

### Tracing

Core Protocols emits OpenTelemetry spans:

- `core_protocols.execute` — Root span for operation
  - `core_protocols.validate` — Input validation
  - `core_protocols.process` — Core processing
  - `core_protocols.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_protocols/`:

- `test_core_protocols.py` — Core unit tests
- `test_core_protocols_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_protocols with real dependencies
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
