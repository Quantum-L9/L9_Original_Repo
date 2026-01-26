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

# External Adapters

> **Tier:** INFRASTRUCTURE | **Path:** `adapters` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                            External Adapters                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │     adapters    │ ───► │  Outbound   │                  │
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

Adapters for external services and APIs

**Purpose:** Provides adapters for integrating with external services.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute adapters tasks
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
adapters/
├── __init__.py
├── tensorglobe_bridge/__init__.py
├── tensorglobe_bridge/adapter.py
├── tensorglobe_bridge/anomaly_guard.py
├── tensorglobe_bridge/schemas.py
├── tensorglobe_bridge/security.py
```

| File               | Purpose                     |
| ------------------ | --------------------------- |
| `__init__.py`      | Core module (PROTECTED)     |
| `anomaly_guard.py` | Anomaly severity levels     |
| `anomaly_guard.py` | Types of anomalies detected |
| `anomaly_guard.py` | Anomaly detection output    |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `AdaptersService`)
- **Functions:** `snake_case` (e.g., `process_adapters_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `anomaly_guard.py` — AnomalySeverity

```python
class AnomalySeverity:
    """Anomaly severity levels"""

    # Key methods:

```

**Lines:** 23-28 in `anomaly_guard.py`

### `anomaly_guard.py` — AnomalyType

```python
class AnomalyType:
    """Types of anomalies detected"""

    # Key methods:

```

**Lines:** 31-37 in `anomaly_guard.py`

### `anomaly_guard.py` — AnomalySignal

```python
class AnomalySignal:
    """Anomaly detection output"""

    # Key methods:

```

**Lines:** 41-49 in `anomaly_guard.py`

### `anomaly_guard.py` — AnomalyDetector

```python
class AnomalyDetector:
    """Statistical anomaly detection for TensorGlobe responses."""

    # Key methods:

    async def __init__(self, ...): ...

    async def detect(self, ...): ...

    async def _check_confidence_collapse(self, ...): ...

    async def _check_latency_breach(self, ...): ...

    async def _check_statistical_outlier(self, ...): ...

```

**Public Methods:** `__init__`, `detect`, `_check_confidence_collapse`, `_check_latency_breach`, `_check_statistical_outlier`

**Lines:** 52-272 in `anomaly_guard.py`

### `adapter.py` — TensorGlobeBridgeAdapter

```python
class TensorGlobeBridgeAdapter:
    """L9 External Cognitive Accelerator."""

    # Key methods:

    async def __init__(self, ...): ...

    async def handle_tensor_request(self, ...): ...

    async def _validate_request_schema(self, ...): ...

    async def _verify_request_signature(self, ...): ...

    async def _call_tensorglobe(self, ...): ...

```

**Public Methods:** `__init__`, `handle_tensor_request`, `_validate_request_schema`, `_verify_request_signature`, `_call_tensorglobe`

**Lines:** 24-229 in `adapter.py`

---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`TensorRequest`** — TensorRequest: Untrusted query to external tensor provider.
- **`TensorResponse`** — TensorResponse from external provider.
- **`TensorRequestPacket`** — TensorRequest wrapped in L9 PacketEnvelope.

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AdaptersRequest(BaseModel):
    """Request model for adapters operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class AdaptersResponse(BaseModel):
    """Response model for adapters operations."""
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

1. **Discovery:** Adapters components are discovered and registered.
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
# Adapters feature flags
L9_ENABLE_ADAPTERS_TRACING: true # Enable detailed tracing
L9_ENABLE_ADAPTERS_METRICS: true # Enable Prometheus metrics
L9_ENABLE_ADAPTERS_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
adapters:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
ADAPTERS_LOG_LEVEL=INFO
ADAPTERS_TIMEOUT=30
ADAPTERS_ENABLED=true
```

---

## API Surface (Public)

See key components for public API details.

### Usage Example

```python
from adapters import AdaptersService

# Initialize
service = AdaptersService()

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

Adapters operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "adapters",
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
| `adapters_operation_duration_ms` | Histogram | Operation latency distribution |
| `adapters_operation_total`       | Counter   | Total operations processed     |
| `adapters_error_total`           | Counter   | Total errors encountered       |
| `adapters_active_connections`    | Gauge     | Current active connections     |

### Tracing

Adapters emits OpenTelemetry spans:

- `adapters.execute` — Root span for operation
  - `adapters.validate` — Input validation
  - `adapters.process` — Core processing
  - `adapters.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/adapters/`:

- `test_adapters.py` — Core unit tests
- `test_adapters_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test adapters with real dependencies
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
