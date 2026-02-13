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

# Local Dashboard

> **Tier:** INFRASTRUCTURE | **Path:** `local_dashboard` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                             Local Dashboard                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   local_dashb   │ ───► │  Outbound   │                  │
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

Local development dashboard

**Purpose:** Provides local web dashboard for development monitoring.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute local dashboard tasks
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

| Module | Purpose             |
| ------ | ------------------- |
| `api/` | Required dependency |

---

## Directory Layout

```
local_dashboard/
├── app.py
```

| File          | Purpose                 |
| ------------- | ----------------------- |
| `__init__.py` | Core module (PROTECTED) |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `LocalDashboardService`)
- **Functions:** `snake_case` (e.g., `process_local_dashboard_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

See source files for component details.

---

## Data Models and Contracts

### Module Constants

| Constant        | Value                                         | Line |
| --------------- | --------------------------------------------- | ---- |
| `L9_API_URL`    | `os.getenv('L9_API_URL', 'http://localhos...` | 63   |
| `L9_API_KEY`    | `os.getenv('L9_API_KEY', '9c4753df3b7ee85...` | 64   |
| `LOCAL_HOST`    | `'127.0.0.1'`                                 | 69   |
| `LOCAL_PORT`    | `5050`                                        | 70   |
| `HTML_TEMPLATE` | `'\n<!DOCTYPE html>\n<html lang="en">\n<h...` | 85   |

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LocalDashboardRequest(BaseModel):
    """Request model for local_dashboard operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class LocalDashboardResponse(BaseModel):
    """Response model for local_dashboard operations."""
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

1. **Discovery:** Local_Dashboard components are discovered and registered.
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
# Local_Dashboard feature flags
L9_ENABLE_LOCAL_DASHBOARD_TRACING: true # Enable detailed tracing
L9_ENABLE_LOCAL_DASHBOARD_METRICS: true # Enable Prometheus metrics
L9_ENABLE_LOCAL_DASHBOARD_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
local_dashboard:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
LOCAL_DASHBOARD_LOG_LEVEL=INFO
LOCAL_DASHBOARD_TIMEOUT=30
LOCAL_DASHBOARD_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `async def index()`

Serve the dashboard.

- **File:** `app.py:537`
- **Async:** Yes

#### `async def chat(request)`

Send message to L9 Agent Executor in Docker.

- **File:** `app.py:543`
- **Async:** Yes

#### `async def health()`

Local health check.

- **File:** `app.py:613`
- **Async:** Yes

### Usage Example

```python
from local_dashboard import LocalDashboardService

# Initialize
service = LocalDashboardService()

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

Local Dashboard operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-29T03:05:45Z",
  "level": "INFO",
  "module": "local_dashboard",
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

| Metric                                  | Type      | Description                    |
| --------------------------------------- | --------- | ------------------------------ |
| `local_dashboard_operation_duration_ms` | Histogram | Operation latency distribution |
| `local_dashboard_operation_total`       | Counter   | Total operations processed     |
| `local_dashboard_error_total`           | Counter   | Total errors encountered       |
| `local_dashboard_active_connections`    | Gauge     | Current active connections     |

### Tracing

Local Dashboard emits OpenTelemetry spans:

- `local_dashboard.execute` — Root span for operation
  - `local_dashboard.validate` — Input validation
  - `local_dashboard.process` — Core processing
  - `local_dashboard.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/local_dashboard/`:

- `test_local_dashboard.py` — Core unit tests
- `test_local_dashboard_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test local_dashboard with real dependencies
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
