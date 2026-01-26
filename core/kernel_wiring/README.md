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

# Kernel Wiring

> **Tier:** CORE | **Path:** `core/kernel_wiring` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                              Kernel Wiring                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_kernel   │ ───► │  Outbound   │                  │
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

Kernel configuration and wiring utilities

**Purpose:** Wires kernel components together during bootstrap.

**What depends on it:** `runtime/kernel_loader.py`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core kernel wiring tasks
- **State management:** Maintain internal state with proper lifecycle
- **Logging:** Emit structured logs for all operations
- **Metrics:** Expose Prometheus-compatible metrics

### What This Module Does NOT Do

- **Authentication** — Handled by `api/auth.py`
- **External communication** — Handled by clients/adapters
- **Scheduling** — Handled by runtime/task_queue.py

### Inbound Dependencies

| Module                     | Purpose          |
| -------------------------- | ---------------- |
| `runtime/kernel_loader.py` | Uses this module |

### Outbound Dependencies

| Module          | Purpose             |
| --------------- | ------------------- |
| `core/kernels/` | Required dependency |

---

## Directory Layout

```
core/kernel_wiring/
├── __init__.py
├── behavioral_wiring.py
├── cognitive_wiring.py
├── developer_wiring.py
├── execution_wiring.py
├── identity_wiring.py
├── master_wiring.py
├── memory_wiring.py
├── packet_protocol_wiring.py
├── safety_wiring.py
├── worldmodel_wiring.py
```

| File          | Purpose                 |
| ------------- | ----------------------- |
| `__init__.py` | Core module (PROTECTED) |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreKernelWiringService`)
- **Functions:** `snake_case` (e.g., `process_core_kernel_wiring_request`)
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

class CoreKernelWiringRequest(BaseModel):
    """Request model for core_kernel_wiring operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreKernelWiringResponse(BaseModel):
    """Response model for core_kernel_wiring operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Wiring is deterministic**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Kernel_Wiring components are discovered and registered.
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
# Core_Kernel_Wiring feature flags
L9_ENABLE_CORE_KERNEL_WIRING_TRACING: true # Enable detailed tracing
L9_ENABLE_CORE_KERNEL_WIRING_METRICS: true # Enable Prometheus metrics
L9_ENABLE_CORE_KERNEL_WIRING_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
core_kernel_wiring:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_KERNEL_WIRING_LOG_LEVEL=INFO
CORE_KERNEL_WIRING_TIMEOUT=30
CORE_KERNEL_WIRING_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def get_output_verbosity()`

No description

- **File:** `behavioral_wiring.py:41`
- **Async:** No

#### `def is_topic_blocked(topic)`

No description

- **File:** `behavioral_wiring.py:49`
- **Async:** No

#### `def get_packet_protocol()`

No description

- **File:** `packet_protocol_wiring.py:41`
- **Async:** No

#### `def get_allowed_event_types()`

No description

- **File:** `packet_protocol_wiring.py:45`
- **Async:** No

#### `def get_default_channel()`

No description

- **File:** `packet_protocol_wiring.py:52`
- **Async:** No

### Usage Example

```python
from core.kernel_wiring import CoreKernelWiringService

# Initialize
service = CoreKernelWiringService()

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

Core Kernel Wiring operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "core.kernel_wiring",
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

| Metric                                     | Type      | Description                    |
| ------------------------------------------ | --------- | ------------------------------ |
| `core_kernel_wiring_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_kernel_wiring_operation_total`       | Counter   | Total operations processed     |
| `core_kernel_wiring_error_total`           | Counter   | Total errors encountered       |
| `core_kernel_wiring_active_connections`    | Gauge     | Current active connections     |

### Tracing

Core Kernel Wiring emits OpenTelemetry spans:

- `core_kernel_wiring.execute` — Root span for operation
  - `core_kernel_wiring.validate` — Input validation
  - `core_kernel_wiring.process` — Core processing
  - `core_kernel_wiring.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_kernel_wiring/`:

- `test_core_kernel_wiring.py` — Core unit tests
- `test_core_kernel_wiring_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_kernel_wiring with real dependencies
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
