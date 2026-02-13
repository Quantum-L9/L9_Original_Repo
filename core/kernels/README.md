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

# Kernel Management

> **Tier:** CORE | **Path:** `core/kernels` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                            Kernel Management                                            │
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

Kernel loading, validation, and integrity verification

**Purpose:** Loads, validates, and manages the kernel stack for agent identity and behavior.

**What depends on it:** `runtime/kernel_loader.py`, `core/agents/executor.py`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core kernels tasks
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
| `core/agents/executor.py`  | Uses this module |

### Outbound Dependencies

| Module             | Purpose             |
| ------------------ | ------------------- |
| `config/kernels/`  | Required dependency |
| `private/kernels/` | Required dependency |

---

## Directory Layout

```
core/kernels/
├── __init__.py
├── integrity.py
├── kernelloader.py
├── prompt_builder.py
├── schemas.py
```

| File                  | Purpose                                            |
| --------------------- | -------------------------------------------------- |
| `kernel_validator.py` | Core module (PROTECTED)                            |
| `__init__.py`         | Core module (PROTECTED)                            |
| `kernelloader.py`     | Protocol for agents that can absorb kernels.       |
| `kernelloader.py`     | Result of a kernel hot-reload operation.           |
| `schemas.py`          | Base model that allows extra fields for forward co |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreKernelsService`)
- **Functions:** `snake_case` (e.g., `process_core_kernels_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `kernelloader.py` — KernelAwareAgent

```python
class KernelAwareAgent:
    """Protocol for agents that can absorb kernels."""

    # Key methods:

    def absorb_kernel(self, ...) -> None: ...

    def set_system_context(self, ...) -> None: ...

```

**Public Methods:** `absorb_kernel`, `set_system_context`

**Lines:** 196-208 in `kernelloader.py`

### `kernelloader.py` — KernelReloadResult

```python
class KernelReloadResult:
    """Result of a kernel hot-reload operation."""

    # Key methods:

    def __init__(self, ...): ...

```

**Public Methods:** `__init__`

**Lines:** 832-849 in `kernelloader.py`

### `schemas.py` — FlexibleModel

```python
class FlexibleModel:
    """Base model that allows extra fields for forward compatibility."""

    # Key methods:

```

**Lines:** 62-65 in `schemas.py`

### `schemas.py` — KernelType

```python
class KernelType:
    """Kernel type identifiers."""

    # Key methods:

```

**Lines:** 73-85 in `schemas.py`

### `schemas.py` — KernelState

```python
class KernelState:
    """Kernel activation states."""

    # Key methods:

```

**Lines:** 88-95 in `schemas.py`

---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`FlexibleModel`** — Base model that allows extra fields for forward compatibility.
- **`WorldModelKernelData`** — World model kernel specific data.

### Exported Symbols (`__all__`)

`BehavioralKernelData`, `CognitiveKernelData`, `DEFAULT_KERNEL_PATH`, `DeveloperKernelData`, `ExecutionKernelData`, `GuardrailConfig`, `IdentityConfig`, `IdentityKernelData`, `IntegrityChange`, `KERNEL_EXTENSIONS`

_...and 55 more_

### Module Constants

| Constant                | Value                                         | Line |
| ----------------------- | --------------------------------------------- | ---- |
| `DEFAULT_KERNEL_PATH`   | `'private'`                                   | 156  |
| `KERNEL_EXTENSIONS`     | `('.yaml', '.yml')`                           | 157  |
| `KERNEL_ORDER`          | `['private/kernels/00_system/01_master_ke...` | 160  |
| `KERNEL_ID_MAP`         | `{'master': '01_master_kernel.yaml', 'ide...` | 174  |
| `REQUIRED_KERNEL_COUNT` | `10`                                          | 188  |
| `KERNEL_HASH_FILE`      | `Path('private/kernel_hashes.json')`          | 66   |
| `HASH_ALGORITHM`        | `'sha256'`                                    | 67   |
| `KERNEL_EXTENSIONS`     | `('.yaml', '.yml')`                           | 68   |

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CoreKernelsRequest(BaseModel):
    """Request model for core_kernels operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreKernelsResponse(BaseModel):
    """Response model for core_kernels operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Kernel YAML must pass schema validation**
- **Kernel load order is deterministic**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Kernels components are discovered and registered.
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
# Core_Kernels feature flags
L9_ENABLE_CORE_KERNELS_TRACING: true # Enable detailed tracing
L9_ENABLE_CORE_KERNELS_METRICS: true # Enable Prometheus metrics
L9_ENABLE_CORE_KERNELS_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
core_kernels:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_KERNELS_LOG_LEVEL=INFO
CORE_KERNELS_TIMEOUT=30
CORE_KERNELS_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def get_kernel_stack() -> KernelStack`

Get or load the kernel stack (singleton). CACHED.

- **File:** `prompt_builder.py:51`
- **Async:** No
- **Returns:** `KernelStack`

#### `def build_identity_section(identity_kernel) -> str`

Build identity section from identity kernel.

- **File:** `prompt_builder.py:58`
- **Async:** No
- **Returns:** `str`

#### `def build_behavioral_section(behavioral_kernel) -> str`

Build behavioral rules from behavioral kernel.

- **File:** `prompt_builder.py:93`
- **Async:** No
- **Returns:** `str`

#### `def build_cognitive_section(cognitive_kernel) -> str`

Build cognitive patterns from cognitive kernel.

- **File:** `prompt_builder.py:145`
- **Async:** No
- **Returns:** `str`

#### `def build_execution_section(execution_kernel) -> str`

Build execution rules from execution kernel.

- **File:** `prompt_builder.py:182`
- **Async:** No
- **Returns:** `str`

### Usage Example

```python
from core.kernels import CoreKernelsService

# Initialize
service = CoreKernelsService()

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

Core Kernels operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-29T03:05:45Z",
  "level": "INFO",
  "module": "core.kernels",
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

| Metric                               | Type      | Description                    |
| ------------------------------------ | --------- | ------------------------------ |
| `core_kernels_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_kernels_operation_total`       | Counter   | Total operations processed     |
| `core_kernels_error_total`           | Counter   | Total errors encountered       |
| `core_kernels_active_connections`    | Gauge     | Current active connections     |

### Tracing

Core Kernels emits OpenTelemetry spans:

- `core_kernels.execute` — Root span for operation
  - `core_kernels.validate` — Input validation
  - `core_kernels.process` — Core processing
  - `core_kernels.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_kernels/`:

- `test_core_kernels.py` — Core unit tests
- `test_core_kernels_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_kernels with real dependencies
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

- `kernel_discovery.py` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- `kernel_validator.py` — Requires human review before merge
- `__init__.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `kernel_validator.py` — PROTECTED: Changes break system invariants
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
