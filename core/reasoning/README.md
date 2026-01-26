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

# Reasoning Engine

> **Tier:** CORE | **Path:** `core/reasoning` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                             Reasoning Engine                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_reason   │ ───► │  Outbound   │                  │
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

ToTH engine, reasoning patterns, and cognitive processing

**Purpose:** Implements Tree-of-Thought reasoning and cognitive processing patterns.

**What depends on it:** `orchestrators/reasoning/`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core reasoning tasks
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
| `orchestrators/reasoning/` | Uses this module |

### Outbound Dependencies

| Module                    | Purpose             |
| ------------------------- | ------------------- |
| `core/agents/executor.py` | Required dependency |

---

## Directory Layout

```
core/reasoning/
├── __init__.py
├── l9_toth_adapter.py
├── toth_engine.py
```

| File             | Purpose                 |
| ---------------- | ----------------------- |
| `toth_engine.py` | Core module (PROTECTED) |
| `__init__.py`    | Core module (PROTECTED) |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreReasoningService`)
- **Functions:** `snake_case` (e.g., `process_core_reasoning_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `toth_engine.py` — ReasoningMode

```python
class ReasoningMode:
    """No description"""

    # Key methods:

```

**Lines:** 61-65 in `toth_engine.py`

### `toth_engine.py` — ModelProvider

```python
class ModelProvider:
    """No description"""

    # Key methods:

```

**Lines:** 67-72 in `toth_engine.py`

### `toth_engine.py` — ToThConfig

```python
class ToThConfig:
    """Production ToTh configuration"""

    # Key methods:

    async def __post_init__(self, ...): ...

```

**Public Methods:** `__post_init__`

**Lines:** 75-90 in `toth_engine.py`

### `toth_engine.py` — ReasoningStep

```python
class ReasoningStep:
    """Individual reasoning step"""

    # Key methods:

    async def __post_init__(self, ...): ...

```

**Public Methods:** `__post_init__`

**Lines:** 93-107 in `toth_engine.py`

### `toth_engine.py` — ReasoningResult

```python
class ReasoningResult:
    """Complete reasoning result"""

    # Key methods:

    async def __post_init__(self, ...): ...

```

**Public Methods:** `__post_init__`

**Lines:** 110-123 in `toth_engine.py`

---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`ModelProvider`** — Data model
- **`CloudModelClient`** — Client for cloud-based language models

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CoreReasoningRequest(BaseModel):
    """Request model for core_reasoning operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreReasoningResponse(BaseModel):
    """Response model for core_reasoning operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Reasoning steps are logged as packets**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Reasoning components are discovered and registered.
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
# Core_Reasoning feature flags
L9_ENABLE_CORE_REASONING_TRACING: true # Enable detailed tracing
L9_ENABLE_CORE_REASONING_METRICS: true # Enable Prometheus metrics
L9_ENABLE_CORE_REASONING_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
core_reasoning:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_REASONING_LOG_LEVEL=INFO
CORE_REASONING_TIMEOUT=30
CORE_REASONING_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `async def main()`

CLI interface for production ToTh engine

- **File:** `toth_engine.py:830`
- **Async:** Yes

### Usage Example

```python
from core.reasoning import CoreReasoningService

# Initialize
service = CoreReasoningService()

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

Core Reasoning operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "core.reasoning",
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
| `core_reasoning_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_reasoning_operation_total`       | Counter   | Total operations processed     |
| `core_reasoning_error_total`           | Counter   | Total errors encountered       |
| `core_reasoning_active_connections`    | Gauge     | Current active connections     |

### Tracing

Core Reasoning emits OpenTelemetry spans:

- `core_reasoning.execute` — Root span for operation
  - `core_reasoning.validate` — Input validation
  - `core_reasoning.process` — Core processing
  - `core_reasoning.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_reasoning/`:

- `test_core_reasoning.py` — Core unit tests
- `test_core_reasoning_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_reasoning with real dependencies
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

- `toth_engine.py` — Requires human review before merge
- `__init__.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `toth_engine.py` — PROTECTED: Changes break system invariants
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
