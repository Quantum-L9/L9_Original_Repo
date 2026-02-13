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

# LangGraph Integration

> **Tier:** INFRASTRUCTURE | **Path:** `langgraph` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       LangGrap Integration                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │langgraph    │ ───► │  Outbound   │                  │
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

LangGraph workflow documentation and integration

**Purpose:** Documents LangGraph integration patterns.

**What depends on it:** `services/research/`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute langgraph tasks
- **State management:** Maintain internal state with proper lifecycle
- **Logging:** Emit structured logs for all operations
- **Metrics:** Expose Prometheus-compatible metrics

### What This Module Does NOT Do

- **Authentication** — Handled by `api/auth.py`
- **External communication** — Handled by clients/adapters
- **Scheduling** — Handled by runtime/task_queue.py

### Inbound Dependencies

| Module               | Purpose          |
| -------------------- | ---------------- |
| `services/research/` | Uses this module |

### Outbound Dependencies

| Module | Purpose                  |
| ------ | ------------------------ |
| —      | No outbound dependencies |

---

## Directory Layout

```
langgraph/
```

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `LanggraphService`)
- **Functions:** `snake_case` (e.g., `process_langgraph_request`)
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

class LanggraphRequest(BaseModel):
    """Request model for langgraph operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class LanggraphResponse(BaseModel):
    """Response model for langgraph operations."""
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

1. **Discovery:** Langgraph components are discovered and registered.
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
# Langgraph feature flags
L9_ENABLE_LANGGRAPH_TRACING: true # Enable detailed tracing
L9_ENABLE_LANGGRAPH_METRICS: true # Enable Prometheus metrics
L9_ENABLE_LANGGRAPH_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
langgraph:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
LANGGRAPH_LOG_LEVEL=INFO
LANGGRAPH_TIMEOUT=30
LANGGRAPH_ENABLED=true
```

---

## API Surface (Public)

See key components for public API details.

### Usage Example

```python
from langgraph import LanggraphService

# Initialize
service = LanggraphService()

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

Langgraph operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-29T03:05:45Z",
  "level": "INFO",
  "module": "langgraph",
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

| Metric                            | Type      | Description                    |
| --------------------------------- | --------- | ------------------------------ |
| `langgraph_operation_duration_ms` | Histogram | Operation latency distribution |
| `langgraph_operation_total`       | Counter   | Total operations processed     |
| `langgraph_error_total`           | Counter   | Total errors encountered       |
| `langgraph_active_connections`    | Gauge     | Current active connections     |

### Tracing

Langgraph emits OpenTelemetry spans:

- `langgraph.execute` — Root span for operation
  - `langgraph.validate` — Input validation
  - `langgraph.process` — Core processing
  - `langgraph.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/langgraph/`:

- `test_langgraph.py` — Core unit tests
- `test_langgraph_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test langgraph with real dependencies
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

- `**/*.md` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- None

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- None

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
