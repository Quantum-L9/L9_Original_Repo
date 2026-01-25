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

# Compliance Engine

> **Tier:** CORE | **Path:** `core/compliance` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                            Compliance Engine                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_compli   │ ───► │  Outbound   │                  │
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

Compliance checking and policy enforcement

**Purpose:** Ensures system operations comply with defined policies.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core compliance tasks
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
| — | No inbound dependencies |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| `core/governance/` | Required dependency |

---

## Directory Layout

```
core/compliance/
├── __init__.py
├── audit_log.py
├── audit_reporter.py
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `audit_reporter.py` | Compliance report for a time period. |
| `audit_reporter.py` | Generates compliance reports from audit trail. |
| `audit_log.py` | Audit logger for Igor commands and high-risk opera |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreComplianceService`)
- **Functions:** `snake_case` (e.g., `process_core_compliance_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `audit_reporter.py` — ComplianceReport

```python
class ComplianceReport:
    """Compliance report for a time period."""
    
    # Key methods:

    async def to_dict(self, ...): ...

```

**Public Methods:** `to_dict`

**Lines:** 49-100 in `audit_reporter.py`

### `audit_reporter.py` — ComplianceReporter

```python
class ComplianceReporter:
    """Generates compliance reports from audit trail."""
    
    # Key methods:

    async def __init__(self, ...): ...

    async def generate_daily_report(self, ...): ...

    async def generate_report(self, ...): ...

    async def _process_commands(self, ...): ...

    async def _process_tool_calls(self, ...): ...

```

**Public Methods:** `__init__`, `generate_daily_report`, `generate_report`, `_process_commands`, `_process_tool_calls`

**Lines:** 103-409 in `audit_reporter.py`

### `audit_log.py` — AuditLogger

```python
class AuditLogger:
    """Audit logger for Igor commands and high-risk operations."""
    
    # Key methods:

    async def __init__(self, ...): ...

    async def log_command(self, ...): ...

    async def log_approval(self, ...): ...

    async def log_tool_execution(self, ...): ...

    async def log_memory_write(self, ...): ...

```

**Public Methods:** `__init__`, `log_command`, `log_approval`, `log_tool_execution`, `log_memory_write`

**Lines:** 56-351 in `audit_log.py`


---

## Data Models and Contracts

Data models are defined in `schemas.py` or inline within service classes.

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CoreComplianceRequest(BaseModel):
    """Request model for core_compliance operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreComplianceResponse(BaseModel):
    """Response model for core_compliance operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Compliance violations are logged**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Compliance components are discovered and registered.
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
# Core_Compliance feature flags
L9_ENABLE_CORE_COMPLIANCE_TRACING: true  # Enable detailed tracing
L9_ENABLE_CORE_COMPLIANCE_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_CORE_COMPLIANCE_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
core_compliance:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_COMPLIANCE_LOG_LEVEL=INFO
CORE_COMPLIANCE_TIMEOUT=30
CORE_COMPLIANCE_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `async def log_command_to_audit(substrate_service, command_id, command_type, user_id, action, risk_level, raw_text, result, error)`

Convenience function to log a command to audit trail.

- **File:** `audit_log.py:354`
- **Async:** Yes


### Usage Example

```python
from core.compliance import CoreComplianceService

# Initialize
service = CoreComplianceService()

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

Core Compliance operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "core.compliance",
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
| `core_compliance_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_compliance_operation_total` | Counter | Total operations processed |
| `core_compliance_error_total` | Counter | Total errors encountered |
| `core_compliance_active_connections` | Gauge | Current active connections |

### Tracing

Core Compliance emits OpenTelemetry spans:

- `core_compliance.execute` — Root span for operation
  - `core_compliance.validate` — Input validation
  - `core_compliance.process` — Core processing
  - `core_compliance.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_compliance/`:
- `test_core_compliance.py` — Core unit tests
- `test_core_compliance_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_compliance with real dependencies
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
