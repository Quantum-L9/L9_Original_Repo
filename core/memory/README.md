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

# Core Memory Utilities

> **Tier:** CORE | **Path:** `core/memory` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                          Core Memory Utilities                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_memory   │ ───► │  Outbound   │                  │
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

Memory abstractions and utilities

**Purpose:** Provides core memory abstractions used by memory subsystem.

**What depends on it:** `memory/`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core memory tasks
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
| `memory/` | Uses this module |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| — | No outbound dependencies |

---

## Directory Layout

```
core/memory/
├── __init__.py
├── runtime.py
├── virtual_context.py
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `runtime.py` | Represents a kernel evolution event for logging. |
| `virtual_context.py` | Memory organization tiers (like OS virtual memory) |
| `virtual_context.py` | Single memory chunk |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreMemoryService`)
- **Functions:** `snake_case` (e.g., `process_core_memory_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `runtime.py` — KernelEvolutionEvent

```python
class KernelEvolutionEvent:
    """Represents a kernel evolution event for logging."""

    # Key methods:

    def __init__(self, ...): ...

    def to_packet_payload(self, ...) -> dict[str, Any]: ...

```

**Public Methods:** `__init__`, `to_packet_payload`

**Lines:** 49-98 in `runtime.py`

### `virtual_context.py` — MemoryTier

```python
class MemoryTier:
    """Memory organization tiers (like OS virtual memory)"""

    # Key methods:

```

**Lines:** 44-49 in `virtual_context.py`

### `virtual_context.py` — Memory

```python
class Memory:
    """Single memory chunk"""

    # Key methods:

```

**Lines:** 53-63 in `virtual_context.py`

### `virtual_context.py` — Context

```python
class Context:
    """Agent execution context (main + working loaded, archival on-demand)"""

    # Key methods:

```

**Lines:** 67-74 in `virtual_context.py`

### `virtual_context.py` — VirtualContextManager

```python
class VirtualContextManager:
    """MemGPT-style virtual context with automatic tier management"""

    # Key methods:

    def __init__(self, ...): ...

    async def load_context(self, ...) -> Context: ...

    async def page_fault_handler(self, ...) -> list[Memory]: ...

    async def evict_to_archival(self, ...) -> None: ...

    async def _evict_lru(self, ...) -> None: ...

```

**Public Methods:** `__init__`, `load_context`, `page_fault_handler`, `evict_to_archival`, `_evict_lru`

**Lines:** 77-305 in `virtual_context.py`


---

## Data Models and Contracts


### Exported Symbols (`__all__`)

`KernelEvolutionEvent`, `get_kernel_evolution_history`, `log_kernel_evolution`

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CoreMemoryRequest(BaseModel):
    """Request model for core_memory operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreMemoryResponse(BaseModel):
    """Response model for core_memory operations."""
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

1. **Discovery:** Core_Memory components are discovered and registered.
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
# Core_Memory feature flags
L9_ENABLE_CORE_MEMORY_TRACING: true  # Enable detailed tracing
L9_ENABLE_CORE_MEMORY_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_CORE_MEMORY_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
core_memory:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_MEMORY_LOG_LEVEL=INFO
CORE_MEMORY_TIMEOUT=30
CORE_MEMORY_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `async def log_kernel_evolution(event_type, agent_id, kernel_ids, previous_hashes, new_hashes, modified_kernels, trigger, success, errors, metadata) -> str | None`

Log a kernel evolution event to the memory substrate.

- **File:** `runtime.py:101`
- **Async:** Yes
- **Returns:** `str | None`

#### `async def get_kernel_evolution_history(agent_id, event_type, limit) -> list[dict[str, Any]]`

Retrieve kernel evolution history from the memory substrate.

- **File:** `runtime.py:220`
- **Async:** Yes
- **Returns:** `list[dict[str, Any]]`


### Usage Example

```python
from core.memory import CoreMemoryService

# Initialize
service = CoreMemoryService()

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

Core Memory operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-29T03:05:45Z",
  "level": "INFO",
  "module": "core.memory",
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
| `core_memory_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_memory_operation_total` | Counter | Total operations processed |
| `core_memory_error_total` | Counter | Total errors encountered |
| `core_memory_active_connections` | Gauge | Current active connections |

### Tracing

Core Memory emits OpenTelemetry spans:

- `core_memory.execute` — Root span for operation
  - `core_memory.validate` — Input validation
  - `core_memory.process` — Core processing
  - `core_memory.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_memory/`:
- `test_core_memory.py` — Core unit tests
- `test_core_memory_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_memory with real dependencies
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
