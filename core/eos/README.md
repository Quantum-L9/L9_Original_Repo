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

# EOS System

> **Tier:** CORE | **Path:** `core/eos` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                EOS System                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │     core_eos    │ ───► │  Outbound   │                  │
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

Execution Operating System components

**Purpose:** Manages execution environment and system resources.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core eos tasks
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
core/eos/
├── __init__.py
├── accountability_engine.py
├── hypergraph_client.py
├── ledger_writer.py
├── schemas.py
```

| File                       | Purpose                                            |
| -------------------------- | -------------------------------------------------- |
| `__init__.py`              | Core module (PROTECTED)                            |
| `hypergraph_client.py`     | EOS-specific hypergraph client for accountability  |
| `ledger_writer.py`         | Immutable ledger writer for EOS accountability eve |
| `accountability_engine.py` | L9 Accountability Engine — Runtime enforcement gat |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreEosService`)
- **Functions:** `snake_case` (e.g., `process_core_eos_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `hypergraph_client.py` — EOSHypergraphClient

```python
class EOSHypergraphClient:
    """EOS-specific hypergraph client for accountability queries."""

    # Key methods:

    def __init__(self, ...): ...

    def available(self, ...) -> bool: ...

    async def check_violations(self, ...) -> dict[str, Any]: ...

    async def get_agent_capabilities(self, ...) -> list[dict[str, Any]]: ...

    async def get_active_prohibitions(self, ...) -> list[dict[str, Any]]: ...

```

**Public Methods:** `__init__`, `available`, `check_violations`, `get_agent_capabilities`, `get_active_prohibitions`

**Lines:** 46-345 in `hypergraph_client.py`

### `ledger_writer.py` — EOSLedgerWriter

```python
class EOSLedgerWriter:
    """Immutable ledger writer for EOS accountability events."""

    # Key methods:

    def __init__(self, ...): ...

    def available(self, ...) -> bool: ...

    def _compute_hash(self, ...) -> str: ...

    async def write(self, ...) -> str | None: ...

    async def write_verdict_entry(self, ...) -> str | None: ...

```

**Public Methods:** `__init__`, `available`, `_compute_hash`, `write`, `write_verdict_entry`

**Lines:** 53-414 in `ledger_writer.py`

### `accountability_engine.py` — AccountabilityEngine

```python
class AccountabilityEngine:
    """L9 Accountability Engine — Runtime enforcement gate."""

    # Key methods:

    def __init__(self, ...): ...

    async def evaluate_action(self, ...) -> tuple[Verdict, list[str]]: ...

    async def _verify_signature(self, ...) -> bool: ...

    async def _check_authority(self, ...) -> tuple[bool, str]: ...

    async def _check_constraints(self, ...) -> list[str]: ...

```

**Public Methods:** `__init__`, `evaluate_action`, `_verify_signature`, `_check_authority`, `_check_constraints`

**Lines:** 32-330 in `accountability_engine.py`

### `schemas.py` — EpistemicObjectType

```python
class EpistemicObjectType:
    """Types of epistemic objects"""

    # Key methods:

```

**Lines:** 18-27 in `schemas.py`

### `schemas.py` — Enforceability

```python
class Enforceability:
    """Enforceability levels"""

    # Key methods:

```

**Lines:** 30-35 in `schemas.py`

---

## Data Models and Contracts

### Exported Symbols (`__all__`)

`AccountabilityEngine`, `ActionEnvelope`, `ActionType`, `AuthorityLevel`, `Condition`, `ConditionType`, `DoctrineSource`, `EOSHypergraphClient`, `EOSLedgerWriter`, `Enforceability`

_...and 13 more_

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CoreEosRequest(BaseModel):
    """Request model for core_eos operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreEosResponse(BaseModel):
    """Response model for core_eos operations."""
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

1. **Discovery:** Core_Eos components are discovered and registered.
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
# Core_Eos feature flags
L9_ENABLE_CORE_EOS_TRACING: true # Enable detailed tracing
L9_ENABLE_CORE_EOS_METRICS: true # Enable Prometheus metrics
L9_ENABLE_CORE_EOS_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
core_eos:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_EOS_LOG_LEVEL=INFO
CORE_EOS_TIMEOUT=30
CORE_EOS_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `async def create_eos_hypergraph_client() -> EOSHypergraphClient`

Factory function to create EOSHypergraphClient with Neo4j.

- **File:** `hypergraph_client.py:353`
- **Async:** Yes
- **Returns:** `EOSHypergraphClient`

#### `async def create_eos_ledger_writer() -> EOSLedgerWriter`

Factory function to create EOSLedgerWriter with SubstrateService.

- **File:** `ledger_writer.py:422`
- **Async:** Yes
- **Returns:** `EOSLedgerWriter`

### Usage Example

```python
from core.eos import CoreEosService

# Initialize
service = CoreEosService()

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

Core Eos operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-29T03:05:45Z",
  "level": "INFO",
  "module": "core.eos",
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

| Metric                           | Type      | Description                    |
| -------------------------------- | --------- | ------------------------------ |
| `core_eos_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_eos_operation_total`       | Counter   | Total operations processed     |
| `core_eos_error_total`           | Counter   | Total errors encountered       |
| `core_eos_active_connections`    | Gauge     | Current active connections     |

### Tracing

Core Eos emits OpenTelemetry spans:

- `core_eos.execute` — Root span for operation
  - `core_eos.validate` — Input validation
  - `core_eos.process` — Core processing
  - `core_eos.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_eos/`:

- `test_core_eos.py` — Core unit tests
- `test_core_eos_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_eos with real dependencies
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
