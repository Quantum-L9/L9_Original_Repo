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

# Accountability & Audit

> **Tier:** CORE | **Path:** `core/accountability` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                          Accountability & Audit                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_accoun   │ ───► │  Outbound   │                  │
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

Accountability tracking and audit trail management

**Purpose:** Tracks agent actions and maintains audit trails for compliance.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core accountability tasks
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

| Module                        | Purpose             |
| ----------------------------- | ------------------- |
| `memory/substrate_service.py` | Required dependency |

---

## Directory Layout

```
core/accountability/
├── __init__.py
```

| File          | Purpose                 |
| ------------- | ----------------------- |
| `__init__.py` | Core module (PROTECTED) |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreAccountabilityService`)
- **Functions:** `snake_case` (e.g., `process_core_accountability_request`)
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

class CoreAccountabilityRequest(BaseModel):
    """Request model for core_accountability operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreAccountabilityResponse(BaseModel):
    """Response model for core_accountability operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **All actions are logged with timestamps**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Accountability components are discovered and registered.
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
# Core_Accountability feature flags
L9_ENABLE_CORE_ACCOUNTABILITY_TRACING: true # Enable detailed tracing
L9_ENABLE_CORE_ACCOUNTABILITY_METRICS: true # Enable Prometheus metrics
L9_ENABLE_CORE_ACCOUNTABILITY_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
core_accountability:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_ACCOUNTABILITY_LOG_LEVEL=INFO
CORE_ACCOUNTABILITY_TIMEOUT=30
CORE_ACCOUNTABILITY_ENABLED=true
```

---

## API Surface (Public)

See key components for public API details.

### Usage Example

```python
from core.accountability import CoreAccountabilityService

# Initialize
service = CoreAccountabilityService()

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

Core Accountability operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-29T03:05:45Z",
  "level": "INFO",
  "module": "core.accountability",
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

| Metric                                      | Type      | Description                    |
| ------------------------------------------- | --------- | ------------------------------ |
| `core_accountability_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_accountability_operation_total`       | Counter   | Total operations processed     |
| `core_accountability_error_total`           | Counter   | Total errors encountered       |
| `core_accountability_active_connections`    | Gauge     | Current active connections     |

### Tracing

Core Accountability emits OpenTelemetry spans:

- `core_accountability.execute` — Root span for operation
  - `core_accountability.validate` — Input validation
  - `core_accountability.process` — Core processing
  - `core_accountability.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_accountability/`:

- `test_core_accountability.py` — Core unit tests
- `test_core_accountability_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_accountability with real dependencies
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
