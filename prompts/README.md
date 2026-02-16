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

# Prompt Library

> **Tier:** INFRASTRUCTURE | **Path:** `prompts` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                              Prompt Library                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │     prompts     │ ───► │  Outbound   │                  │
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

Prompt templates and management

**Purpose:** Stores and manages prompt templates for agents.

**What depends on it:** `core/agents/`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute prompts tasks
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
| `core/agents/` | Uses this module |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| — | No outbound dependencies |

---

## Directory Layout

```
prompts/
```



### Naming Conventions

- **Classes:** `PascalCase` (e.g., `PromptsService`)
- **Functions:** `snake_case` (e.g., `process_prompts_request`)
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
from datetime import datetime, timezone

class PromptsRequest(BaseModel):
    """Request model for prompts operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class PromptsResponse(BaseModel):
    """Response model for prompts operations."""
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

1. **Discovery:** Prompts components are discovered and registered.
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
# Prompts feature flags
L9_ENABLE_PROMPTS_TRACING: true  # Enable detailed tracing
L9_ENABLE_PROMPTS_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_PROMPTS_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
prompts:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
PROMPTS_LOG_LEVEL=INFO
PROMPTS_TIMEOUT=30
PROMPTS_ENABLED=true
```

---

## API Surface (Public)

See key components for public API details.

### Usage Example

```python
from prompts import PromptsService

# Initialize
service = PromptsService()

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

Prompts operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-14T08:25:39Z",
  "level": "INFO",
  "module": "prompts",
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
| `prompts_operation_duration_ms` | Histogram | Operation latency distribution |
| `prompts_operation_total` | Counter | Total operations processed |
| `prompts_error_total` | Counter | Total errors encountered |
| `prompts_active_connections` | Gauge | Current active connections |

### Tracing

Prompts emits OpenTelemetry spans:

- `prompts.execute` — Root span for operation
  - `prompts.validate` — Input validation
  - `prompts.process` — Core processing
  - `prompts.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/prompts/`:
- `test_prompts.py` — Core unit tests
- `test_prompts_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test prompts with real dependencies
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

- `**/*.txt` — Application logic, safe to modify
- `**/*.md` — Application logic, safe to modify
- `**/*.yaml` — Application logic, safe to modify

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
