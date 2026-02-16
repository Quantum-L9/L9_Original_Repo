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

# Coordination & Events

> **Tier:** CORE | **Path:** `core/coordination` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                          Coordination & Events                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_coordi   │ ───► │  Outbound   │                  │
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

Event bus, coordination primitives, and inter-module communication

**Purpose:** Provides event bus and coordination primitives for inter-module communication.

**What depends on it:** `orchestrators/`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core coordination tasks
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
| `orchestrators/` | Uses this module |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| `runtime/redis_client.py` | Required dependency |

---

## Directory Layout

```
core/coordination/
├── __init__.py
├── agent_mediator.py
├── event_queue.py
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `agent_mediator.py` | Message structure for agent-to-agent communication |
| `agent_mediator.py` | Track message delivery status. |
| `agent_mediator.py` | Mediator for agent-to-agent communication. |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreCoordinationService`)
- **Functions:** `snake_case` (e.g., `process_core_coordination_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `agent_mediator.py` — Message

```python
class Message:
    """Message structure for agent-to-agent communication."""

    # Key methods:

```

**Lines:** 96-118 in `agent_mediator.py`

### `agent_mediator.py` — MessageDeliveryStatus

```python
class MessageDeliveryStatus:
    """Track message delivery status."""

    # Key methods:

```

**Lines:** 122-129 in `agent_mediator.py`

### `agent_mediator.py` — AgentMediator

```python
class AgentMediator:
    """Mediator for agent-to-agent communication."""

    # Key methods:

    def __init__(self, ...): ...

    def register_agent(self, ...) -> None: ...

    def unregister_agent(self, ...) -> None: ...

    def subscribe(self, ...) -> None: ...

    def unsubscribe(self, ...) -> None: ...

```

**Public Methods:** `__init__`, `register_agent`, `unregister_agent`, `subscribe`, `unsubscribe`

**Lines:** 137-454 in `agent_mediator.py`

### `event_queue.py` — EventKind

```python
class EventKind:
    """Event types in the coordination system"""

    # Key methods:

```

**Lines:** 46-60 in `event_queue.py`

### `event_queue.py` — Event

```python
class Event:
    """Event in the async coordination system"""

    # Key methods:

    def __post_init__(self, ...): ...

```

**Public Methods:** `__post_init__`

**Lines:** 64-84 in `event_queue.py`


---

## Data Models and Contracts


### Exported Symbols (`__all__`)

`Event`, `EventKind`, `EventQueue`, `EventRouter`, `init_event_driven_coordination`

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class CoreCoordinationRequest(BaseModel):
    """Request model for core_coordination operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreCoordinationResponse(BaseModel):
    """Response model for core_coordination operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Events are typed**
- **Event delivery is at-least-once**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Coordination components are discovered and registered.
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
# Core_Coordination feature flags
L9_ENABLE_CORE_COORDINATION_TRACING: true  # Enable detailed tracing
L9_ENABLE_CORE_COORDINATION_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_CORE_COORDINATION_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
core_coordination:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_COORDINATION_LOG_LEVEL=INFO
CORE_COORDINATION_TIMEOUT=30
CORE_COORDINATION_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `async def get_agent_mediator() -> AgentMediator`

Get the singleton AgentMediator instance.

- **File:** `agent_mediator.py:472`
- **Async:** Yes
- **Returns:** `AgentMediator`

#### `async def close_agent_mediator() -> None`

Close the AgentMediator singleton.

- **File:** `agent_mediator.py:488`
- **Async:** Yes
- **Returns:** `None`

#### `async def init_event_driven_coordination(app_state) -> EventQueue`

Initialize event-driven coordination at startup

- **File:** `event_queue.py:266`
- **Async:** Yes
- **Returns:** `EventQueue`

#### `async def event_queue_health(event_queue) -> dict`

Health check for event queue

- **File:** `event_queue.py:282`
- **Async:** Yes
- **Returns:** `dict`


### Usage Example

```python
from core.coordination import CoreCoordinationService

# Initialize
service = CoreCoordinationService()

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

Core Coordination operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-14T08:25:39Z",
  "level": "INFO",
  "module": "core.coordination",
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
| `core_coordination_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_coordination_operation_total` | Counter | Total operations processed |
| `core_coordination_error_total` | Counter | Total errors encountered |
| `core_coordination_active_connections` | Gauge | Current active connections |

### Tracing

Core Coordination emits OpenTelemetry spans:

- `core_coordination.execute` — Root span for operation
  - `core_coordination.validate` — Input validation
  - `core_coordination.process` — Core processing
  - `core_coordination.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_coordination/`:
- `test_core_coordination.py` — Core unit tests
- `test_core_coordination_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_coordination with real dependencies
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
